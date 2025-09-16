# llm_cpu.py
# Инференс Qwen2.5-3B-Instruct + ваш LoRA-адаптер на CPU (Windows/без CUDA)

import os
import threading
from typing import Optional, List

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Убираем ворнинг про symlink в HF cache на Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BASE_MODEL = os.environ.get("BASE_MODEL", r"models/Qwen2.5-3B-Instruct")
ADAPTER_DIR = os.environ.get("ADAPTER_DIR", r"models/qwen25_3b_lora_fast30")

SYSTEM_PROMPT = (
    "Ты ассистент секции КОРП. Отвечай кратко и по делу. "
    "Если в запросе есть опечатки — молча исправь и решай задачу по исправленному тексту; "
    "в ответе добавляй строку «Исправления: …» (если были). "
    "Всегда добавляй раздел «Источники:» со списком использованных материалов. "
    "Если вопрос выходит за рамки КОРП/223-ФЗ/регламентов/гайдов/ЭП/регистрации/имущественных торгов — честно скажи об этом."
)

# На CPU надёжнее float32. Ограничим потоки 2–4, чтобы не «класть» веб-сервер.
torch.set_num_threads(min(4, max(1, (os.cpu_count() or 4))))
DTYPE = torch.float32

_tokenizer = None
_model = None
_eos_ids: List[int] = []
_gen_lock = threading.Lock()  # синхронизация одновременных генераций


def _collect_eos_ids(tok: AutoTokenizer) -> List[int]:
    """Собираем все валидные EOS для Qwen (и совместимых)."""
    ids: List[int] = []
    candidates = [
        "<|im_end|>",          # Qwen chat end token
        "<|endoftext|>",       # общий (часто = eos_token)
        tok.eos_token,         # что прописано в токенизаторе
    ]
    for c in candidates:
        if c is None:
            continue
        tid = tok.convert_tokens_to_ids(c) if isinstance(c, str) else c
        if isinstance(tid, int) and tid >= 0 and tid not in ids:
            ids.append(tid)
    # Гарантируем, что числовой eos_token_id тоже включён
    if isinstance(tok.eos_token_id, int) and tok.eos_token_id not in ids:
        ids.append(tok.eos_token_id)
    # Некоторые токенизаторы возвращают список eos — тоже учитываем
    if isinstance(tok.eos_token_id, list):
        for t in tok.eos_token_id:
            if isinstance(t, int) and t not in ids:
                ids.append(t)
    return ids or [tok.eos_token_id]  # fallback


def _load_once():
    global _tokenizer, _model, _eos_ids
    if _tokenizer is not None and _model is not None:
        return _tokenizer, _model

    print("[LLM] Loading tokenizer:", BASE_MODEL, flush=True)
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"

    print("[LLM] Loading base model on CPU (fp32):", BASE_MODEL, flush=True)
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=DTYPE,
        device_map="cpu",
        trust_remote_code=True,
        attn_implementation="eager",   # на CPU безопаснее eager
        low_cpu_mem_usage=True,
    )

    if ADAPTER_DIR and os.path.isdir(ADAPTER_DIR):
        print("[LLM] Attaching LoRA adapter:", ADAPTER_DIR, flush=True)
        mdl = PeftModel.from_pretrained(base, ADAPTER_DIR)
    else:
        print("[LLM] WARNING: adapter dir not found, running BASE model only.")
        mdl = base

    mdl.eval()

    # Собираем ВСЕ валидные EOS и нормализуем конфиг
    eos_ids = _collect_eos_ids(tok)
    gc = mdl.generation_config
    gc.eos_token_id = eos_ids
    gc.pad_token_id = tok.eos_token_id
    gc.top_k = None
    gc.top_p = 1.0
    gc.temperature = 1.0
    gc.repetition_penalty = 1.0
    gc.no_repeat_ngram_size = None

    _tokenizer, _model, _eos_ids = tok, mdl, eos_ids
    print(f"[LLM] Ready. EOS = {eos_ids}", flush=True)
    return _tokenizer, _model


def generate_answer(
    question: str,
    category: str = "regs",
    subcat: Optional[str] = None,
    max_new_tokens: int = 256,
    min_new_tokens: int = 64,      # гарантируем хотя бы 64 новых токена
    deterministic: bool = True,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    """
    Возвращает чистый текст ответа (без системных токенов)
    """
    tok, model = _load_once()

    user = f"Категория: {category}"
    if subcat:
        user += f"\nПодкатегория: {subcat}"
    user += f"\nВопрос: {question}"

    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tok([prompt], return_tensors="pt")
    inputs = {k: v.to("cpu") for k, v in inputs.items()}

    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "min_new_tokens": max(0, min_new_tokens or 0),
        "eos_token_id": _eos_ids,
        "pad_token_id": tok.eos_token_id,
    }
    if deterministic:
        gen_kwargs.update({
            "do_sample": False,
            "repetition_penalty": 1.05,
            "no_repeat_ngram_size": 4,
        })
    else:
        gen_kwargs.update({
            "do_sample": True,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": 1.12,
            "no_repeat_ngram_size": 6,
        })

    with _gen_lock:  # важно: одна генерация за раз на CPU
        with torch.inference_mode():
            out = model.generate(**inputs, **gen_kwargs)

    gen_ids = out[0][inputs["input_ids"].shape[1]:]
    text = tok.decode(gen_ids, skip_special_tokens=True).strip()

    # Подстраховка от «залипаний»
    if len(text) < 3 or len(set(text)) <= 3:
        with _gen_lock:
            with torch.inference_mode():
                out = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    min_new_tokens=max(0, min_new_tokens or 0),
                    do_sample=True,
                    temperature=0.85,
                    top_p=0.95,
                    repetition_penalty=1.15,
                    no_repeat_ngram_size=6,
                    eos_token_id=_eos_ids,
                    pad_token_id=tok.eos_token_id,
                )
        gen_ids = out[0][inputs["input_ids"].shape[1]:]
        text = tok.decode(gen_ids, skip_special_tokens=True).strip()

    return text


def get_generator():
    _load_once()

    class _Gen:
        def __call__(self, question, category="regs", subcat=None, **kw):
            return generate_answer(question, category, subcat, **kw)

    return _Gen()

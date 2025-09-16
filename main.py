# main.py
from __future__ import annotations

import os
import random
import smtplib
import bcrypt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, redirect, request, url_for, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import func

from forms.user import RegisterForm, LoginForm, ChangePasswordEmailForm, CodeForm
from data.users import User, Chat
from data import db_session

# ==================== ЛЕНИВАЯ ЗАГРУЗКА LLM (важно: без двойного старта) ====================
LLM = None  # будет создан при первом обращении к /api/generate

def get_llm_singleton():
    """
    Загружаем генератор один раз при первом вызове.
    Ничего не грузим на уровне импорта модуля, чтобы Flask не дублировал.
    """
    global LLM
    if LLM is None:
        from llm_cpu import get_generator  # импорт тут, не наверху!
        LLM = get_generator()
    return LLM

# ==================== APP / LOGIN ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = '192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/blogs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# (опционально — если локально без https)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['REMEMBER_COOKIE_SECURE'] = False

login_manager = LoginManager()
login_manager.init_app(app)
db_session.global_init("db/blogs.db")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)

# ==================== MAIL ====================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "dnevnik.dostizheniy@gmail.com"
SENDER_PASSWORD = "dbpk ykew voql kljr"


def ros_email_html(title: str, lead: str, code: str | None = None, extra_html: str = "") -> str:
    code_block = ""
    if code:
        code_block = f"""
        <div style="text-align:center;margin:24px 0;">
          <div style="display:inline-block;padding:14px 22px;border-radius:12px;
                      background:#0F1324;color:#00F0FF;font-weight:800;
                      font-size:24px;letter-spacing:3px;border:1px solid rgba(255,255,255,.08);
                      font-family:'Segoe UI',Roboto,Arial,sans-serif;">
            {code}
          </div>
        </div>"""
    return f"""
    <html>
    <body style="margin:0;padding:24px;background:#0A0F1F;font-family:'Segoe UI',Roboto,Arial,sans-serif;color:#E8ECF3;">
      <div style="max-width:720px;margin:0 auto;">
        <div style="text-align:center;margin-bottom:16px;">
          <div style="display:inline-block;padding:8px 14px;border-radius:999px;background:rgba(0,240,255,.08);
                      color:#00F0FF;border:1px solid rgba(0,240,255,.25);font-weight:700;">
            RLT.Tender_Guide
          </div>
        </div>
        <div style="background:#101426;border:1px solid rgba(255,255,255,.08);border-radius:16px;overflow:hidden;">
          <div style="padding:22px 22px 10px;">
            <h2 style="margin:0 0 6px 0;font-weight:800;color:#E8ECF3;">{title}</h2>
            <p style="margin:0;color:#A9B1C6;line-height:1.6;">{lead}</p>
            {code_block}
            {extra_html}
            <p style="margin:18px 0 0;color:#A9B1C6;line-height:1.6;">
              Если вы не запрашивали это действие, просто проигнорируйте письмо.
            </p>
          </div>
          <div style="background:#0F1324;border-top:1px solid rgba(255,255,255,.06);
                      padding:14px 22px;color:#A9B1C6;text-align:center;">
            Это автоматическое письмо. Отвечать на него не требуется.
          </div>
        </div>
      </div>
    </body>
    </html>"""


def send_mail(recipient_email: str, subject: str, html: str) -> None:
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
        smtp.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())

# ==================== ROUTES (UI) ====================
@app.route("/")
def index():
    return render_template("index.html", title='RLT.Tender_Guide (КОРП)')


@app.route('/privacy-policy')
def policy():
    return render_template("privacy-policy.html", title='Политика конфиденциальности')

# ==================== REGISTER / VERIFY ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit() and request.method == 'POST':
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")

        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пользователь с такой электронной почтой уже зарегистрирован")

        verification_code = str(random.randint(10000, 99999))
        session['temp_user'] = {
            'email': form.email.data,
            'password': form.password.data,
            'verification_code': verification_code
        }
        try:
            html = ros_email_html(
                title="Код подтверждения",
                lead="Вы начали регистрацию в RLT.Tender_Guide. Введите код для подтверждения адреса.",
                code=verification_code
            )
            send_mail(form.email.data, "Код подтверждения для регистрации", html)
        except Exception:
            pass

        return redirect(f"/verify_registration_code?email={form.email.data}")

    return render_template('register.html', title='Регистрация', form=form)


@app.route('/verify_registration_code', methods=['GET', 'POST'])
def verify_registration_code():
    email = request.args.get('email')
    if not email:
        return "Email не предоставлен", 400

    form = CodeForm()

    if request.method == 'POST':
        input_code = (request.form.get('code') or '').strip()
        temp_user = session.get('temp_user')

        if not temp_user or temp_user.get('email') != email:
            return render_template('verify_registration_code.html', title='Проверка кода', form=form,
                                   message="Ошибка: данные регистрации не найдены.", email=email)

        real_code = str(temp_user.get('verification_code', '')).strip()
        if input_code == real_code:
            db_sess = db_session.create_session()
            user = User(email=temp_user['email'])
            user.set_password(temp_user['password'])
            db_sess.add(user)
            db_sess.commit()
            session.pop('temp_user', None)
            return redirect(url_for('login'))
        else:
            new_code = str(random.randint(10000, 99999))
            temp_user['verification_code'] = new_code
            session['temp_user'] = temp_user
            try:
                html = ros_email_html(
                    title="Новый код подтверждения",
                    lead="Вы ввели неверный код. Отправили новый код подтверждения.",
                    code=new_code
                )
                send_mail(email, "Новый код подтверждения для регистрации", html)
                return render_template('verify_registration_code.html', title='Проверка кода', form=form,
                                       message="Неверный код. Новый код отправлен на почту.", email=email)
            except Exception:
                return render_template('verify_registration_code.html', title='Проверка кода', form=form,
                                       message="Ошибка при отправке нового кода. Попробуйте ещё раз.",
                                       email=email)

    return render_template('verify_registration_code.html', title='Проверка кода', form=form, email=email)

# ==================== LOGIN / LOGOUT ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(
            func.replace(User.email, " ", "") == form.email.data.replace(" ", "")
        ).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")

        return render_template('login.html', message="Неправильный логин или пароль", form=form)

    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")

# ==================== CHANGE PASSWORD ====================
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired

class CodeForm1(FlaskForm):
    code = StringField('Код с почты', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired()])
    submit = SubmitField('Проверить код')

@app.route('/change_password_email', methods=['GET', 'POST'])
def change_password_email():
    form = ChangePasswordEmailForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user:
            verification_code = str(random.randint(10000, 99999))
            hashed_code = bcrypt.hashpw(verification_code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.code = hashed_code
            db_sess.commit()

            try:
                html = ros_email_html(
                    title="Код подтверждения для смены пароля",
                    lead="Введите код ниже, чтобы продолжить смену пароля.",
                    code=verification_code
                )
                send_mail(user.email, "Код подтверждения для смены пароля", html)
                return redirect(f"/verify_code?email={user.email}")
            except Exception:
                return render_template('email_parol.html', title='Смена пароля', form=form,
                                       message="Ошибка при отправке кода. Попробуйте ещё раз.")
        else:
            return render_template('email_parol.html', title='Смена пароля', form=form,
                                   message="Пользователь с таким email не найден")

    return render_template('email_parol.html', title='Смена пароля', form=form)


@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    email = request.args.get('email')
    if not email:
        return "Email не предоставлен", 400

    form = CodeForm1()

    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == email).first()

        if user:
            if user.code:
                if bcrypt.checkpw(form.code.data.encode('utf-8'), user.code.encode('utf-8')):
                    user.set_password(form.new_password.data)
                    user.code = None
                    db_sess.commit()
                    return redirect(url_for('login'))
                else:
                    verification_code = str(random.randint(10000, 99999))
                    user.code = bcrypt.hashpw(verification_code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    db_sess.commit()

                    try:
                        html = ros_email_html(
                            title="Новый код подтверждения",
                            lead="Вы ввели неверный код. Отправили новый.",
                            code=verification_code
                        )
                        send_mail(user.email, "Новый код подтверждения для смены пароля", html)
                        return render_template('proverka_code.html', title='Смена пароля', form=form,
                                               message="Неверный код. Новый код отправлен на почту.", email=email)
                    except Exception:
                        return render_template('proverka_code.html', title='Смена пароля', form=form,
                                               message="Ошибка при отправке нового кода. Попробуйте ещё раз.",
                                               email=email)
            else:
                return render_template('proverka_code.html', title='Смена пароля', form=form,
                                       message="Для этого email код не запрашивался.", email=email)
        else:
            return render_template('proverka_code.html', title='Смена пароля', form=form,
                                   message="Пользователь с таким email не найден.", email=email)

    return render_template('proverka_code.html', title='Смена пароля', form=form, email=email)

# ==================== CHAT PERSIST ====================
@app.route('/api/chat/send', methods=['POST'])
def api_chat_send():
    payload = request.json or request.form
    text = (payload.get('text') or '').strip()
    role = (payload.get('role') or 'user').strip().lower()

    if not text:
        return jsonify({"ok": False, "error": "empty_text"}), 400

    if not current_user.is_authenticated:
        return jsonify({"ok": True, "skipped": "guest"}), 200

    role_tag = 'USER'
    if role in ('operator', 'op', 'assistant', 'support'):
        role_tag = 'OP'

    db_sess = db_session.create_session()
    msg = Chat()
    msg.tekst = f"{role_tag}: {text}"
    msg.user_id = current_user.id
    db_sess.add(msg)
    db_sess.commit()
    print(msg.tekst)
    return jsonify({"ok": True, "id": msg.id, "user_id": msg.user_id, "tekst": msg.tekst})


@app.route('/api/chat/history', methods=['GET'])
@login_required
def api_chat_history():
    db_sess = db_session.create_session()
    rows = db_sess.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.id.asc()).all()

    data = [{"id": r.id, "tekst": r.tekst, "user_id": r.user_id} for r in rows]
    return jsonify({"ok": True, "items": data})

# ==================== LLM GENERATION API ====================
@app.route('/api/generate', methods=['POST'])
def api_generate():
    """
    JSON: { "question": "...", "category": "regs", "subcat": null,
            "deterministic": true, "max_new_tokens": 220 }
    """
    data = request.get_json(silent=True) or {}
    q = (data.get("question") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty_question"}), 400

    category = (data.get("category") or "regs").strip()
    subcat = data.get("subcat")
    deterministic = bool(data.get("deterministic", True))
    max_new_tokens = int(data.get("max_new_tokens", 220))

    try:
        llm = get_llm_singleton()
        text = llm(q, category=category, subcat=subcat,
                   deterministic=deterministic, max_new_tokens=max_new_tokens)
        return jsonify({"ok": True, "text": text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ==================== RUN ====================
def main():
    db_session.global_init("db/blogs.db")
    # Важно: отключаем reloader, чтобы не было двойной загрузки модели.
    app.run(host='0.0.0.0', port=5000, threaded=True,
            debug=False, use_reloader=False)

if __name__ == '__main__':
    main()

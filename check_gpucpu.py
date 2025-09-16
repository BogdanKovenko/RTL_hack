import torch, platform
print("Python:", platform.python_version())
print("Torch version:", torch.__version__)
print("CUDA is_available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU name:", torch.cuda.get_device_name(0))
    print("GPU capability:", torch.cuda.get_device_capability(0))
else:
    print("CUDA not available (CPU only).")

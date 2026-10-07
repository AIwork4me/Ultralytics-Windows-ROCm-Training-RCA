import os
import sys

print("python:", sys.executable)
print("sys.prefix:", sys.prefix)
print("sys.base_prefix:", sys.base_prefix)
print("CONDA_DEFAULT_ENV:", os.environ.get("CONDA_DEFAULT_ENV"))
print("CONDA_PREFIX:", os.environ.get("CONDA_PREFIX"))

try:
    import torch
    import torchvision
    import ultralytics

    print("torch:", torch.__version__)
    print("hip:", torch.version.hip)
    print("cuda:", torch.version.cuda)
    print("torchvision:", torchvision.__version__)
    print("ultralytics:", ultralytics.__version__)
    print("cuda_available:", torch.cuda.is_available())
    print(
        "device:",
        torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    )
    print("torch_location:", os.path.dirname(torch.__file__))
    print("ultralytics_location:", os.path.dirname(ultralytics.__file__))
except Exception as e:
    print("IMPORT-FAILURE:", type(e).__name__, e)

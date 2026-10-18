"""
Automated environment installer for LexisEdge.
Detects Python version (3.12 vs 3.14+) and installs compatible wheels cleanly.
"""

import sys
import subprocess

def run_cmd(cmd):
    print(f"Running: {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"Command failed with code {res.returncode}")
        sys.exit(res.returncode)

def main():
    py_ver = sys.version_info
    print(f"Detected Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")

    if py_ver.major != 3 or py_ver.minor < 10:
        print("ERROR: Python 3.10+ (64-bit) is required.")
        sys.exit(1)

    print("\n[1/3] Upgrading pip, setuptools, wheel...")
    run_cmd(f'"{sys.executable}" -m pip install --upgrade pip setuptools wheel')

    print("\n[2/3] Installing core dependencies...")
    if py_ver.minor >= 13:
        # Python 3.13/3.14: install OCR deps with --no-deps for rapidocr
        run_cmd(
            f'"{sys.executable}" -m pip install fastapi uvicorn python-multipart pydantic '
            f'PyMuPDF pillow llama-cpp-python huggingface-hub pytest onnxruntime opencv-python shapely pyclipper'
        )
        run_cmd(f'"{sys.executable}" -m pip install rapidocr-onnxruntime --no-deps')
    else:
        # Python 3.10 - 3.12: standard install
        run_cmd(f'"{sys.executable}" -m pip install -r backend/requirements.txt')

    print("\n[3/3] Verifying core imports...")
    test_code = (
        "import fitz; "
        "import llama_cpp; "
        "from backend.app.parser import HAS_RAPID_OCR; "
        "print('All core dependencies successfully imported! OCR available:', HAS_RAPID_OCR)"
    )
    run_cmd(f'"{sys.executable}" -c "{test_code}"')
    print("\nSetup complete! You can now run 'python download_model.py' to acquire the model.")

if __name__ == "__main__":
    main()

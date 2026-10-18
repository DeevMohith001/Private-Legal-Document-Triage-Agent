"""
ZeroDay OSS Hacktoberfest 2026 — Track PS2: Private Legal Document Triage Agent
Model Acquisition & Verification Script.

Downloads the verified Google Gemma 3n E2B (Q3_K_M GGUF, 2.19 GB) model
directly to backend/models/ for 100% on-device CPU inference.
"""

import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MODEL_REPO = "bartowski/google_gemma-3n-E2B-it-GGUF"
MODEL_FILE = "google_gemma-3n-E2B-it-Q3_K_M.gguf"
TARGET_DIR = os.path.join(os.path.dirname(__file__), "backend", "models")
TARGET_PATH = os.path.join(TARGET_DIR, MODEL_FILE)
MIN_EXPECTED_SIZE_BYTES = 2_000_000_000  # ~2.19 GB

def verify_or_download_model():
    print("=" * 80)
    print("LexisEdge — Gemma 3n Model Acquisition & Verification")
    print("=" * 80)
    print(f"Target Directory: {TARGET_DIR}")
    print(f"Model Filename  : {MODEL_FILE}")
    print(f"Repository      : {MODEL_REPO}")
    print("-" * 80)

    os.makedirs(TARGET_DIR, exist_ok=True)

    if os.path.exists(TARGET_PATH):
        file_size = os.path.getsize(TARGET_PATH)
        file_size_mb = file_size / (1024 * 1024)
        if file_size >= MIN_EXPECTED_SIZE_BYTES:
            print(f"[STATUS] Model weights ALREADY PRESENT on disk!")
            print(f"         Location : {TARGET_PATH}")
            print(f"         Size     : {file_size_mb:.1f} MB ({file_size:,} bytes)")
            print("         Status   : Verified and Ready for local inference.")
            print("=" * 80)
            return TARGET_PATH
        else:
            print(f"[WARNING] Existing model file is incomplete ({file_size_mb:.1f} MB). Re-downloading...")

    print("[INFO] Starting download from Hugging Face Hub (No credentials/API key required)...")
    print("       Quantization: Q3_K_M (Optimized for 8 GB RAM CPU-only execution)")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[ERROR] huggingface_hub is not installed. Please run:")
        print("        pip install huggingface_hub")
        sys.exit(1)

    try:
        downloaded_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            local_dir=TARGET_DIR,
        )
        file_size = os.path.getsize(downloaded_path)
        print("\n" + "=" * 80)
        print("[SUCCESS] Gemma 3n model downloaded successfully!")
        print(f"          Saved to: {downloaded_path}")
        print(f"          Size    : {file_size / (1024*1024):.1f} MB")
        print("=" * 80)
        return downloaded_path
    except Exception as e:
        print(f"\n[ERROR] Model download failed: {e}")
        print("Manual download instructions:")
        print(f"1. Download '{MODEL_FILE}' from https://huggingface.co/{MODEL_REPO}")
        print(f"2. Place the file inside: {TARGET_DIR}/")
        sys.exit(1)

if __name__ == "__main__":
    verify_or_download_model()

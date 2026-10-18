"""
Minimal Gemma 3n Inference Verification Script.
Measures model loading latency, token generation speed, and response output on CPU.
"""

import sys
import time
from llama_cpp import Llama
from backend.app.inference import get_model_path, is_model_available

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def test_inference():
    print("=" * 80)
    print("Minimal Gemma 3n Local Inference Verification")
    print("=" * 80)

    model_path = get_model_path()
    if not is_model_available():
        print(f"[ERROR] Model file not found at: {model_path}")
        print("Run 'python download_model.py' to acquire the weights.")
        sys.exit(1)

    print(f"Loading Gemma 3n model from: {model_path}")
    t0 = time.perf_counter()
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,
        n_threads=4,
        verbose=False,
    )
    t_load = time.perf_counter() - t0
    print(f"[BENCHMARK] Model loaded into CPU memory in: {t_load:.2f} seconds")

    prompt = (
        "<start_of_turn>user\n"
        "Explain in one concise sentence what a 'liquidated damages' clause means in a contract."
        "<end_of_turn>\n"
        "<start_of_turn>model\n"
    )

    print("\nGenerating response with on-device CPU inference...")
    t1 = time.perf_counter()
    output = llm(
        prompt,
        max_tokens=80,
        temperature=0.2,
        stop=["<end_of_turn>"],
    )
    t_gen = time.perf_counter() - t1

    response_text = output["choices"][0]["text"].strip()
    tokens_generated = output["usage"]["completion_tokens"]
    tok_per_sec = tokens_generated / max(0.01, t_gen)

    print("\n" + "-" * 80)
    print(f"GEMMA 3n RESPONSE ({tokens_generated} tokens):")
    print("-" * 80)
    print(response_text)
    print("-" * 80)
    print(f"[METRICS] Inference Time   : {t_gen:.2f} seconds")
    print(f"[METRICS] Generation Speed : {tok_per_sec:.2f} tokens/second")
    print("=" * 80)
    print("VERIFICATION RESULT: REAL LOCAL GEMMA INFERENCE CONFIRMED ON CPU!\n")

if __name__ == "__main__":
    test_inference()

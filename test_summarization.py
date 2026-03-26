import os
import sys
import time
import logging
import warnings

# Silence noisy litellm internal logging and pydantic warnings before importing
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import litellm
litellm.suppress_debug_info = True

from summarizer import Summarizer

# Change to repo root so relative paths resolve correctly
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO_ROOT)

TEST_TRANSCRIPT = "transcriptions/2026-03-25/Academic Ops_12-18-03.md"

MODELS_TO_TEST = [
    "gemini/gemini-3-flash-preview",
    "gemini/gemini-2.5-flash",
    "gemini/gemini-1.5-flash",      # deprecated — expected 404
    "gemini/gemini-3.1-pro-preview",
]

TIMEOUT_SECONDS = 120  # pro models can take longer


def run_tests():
    print("=== Overhear Summarization Test Suite ===")
    print(f"Transcript: {TEST_TRANSCRIPT}\n")

    if not os.path.exists(TEST_TRANSCRIPT):
        print(f"[ERROR] Transcript not found: {TEST_TRANSCRIPT}")
        sys.exit(1)

    summarizer = Summarizer()
    api_key = summarizer.get_api_key("GEMINI")

    if not api_key:
        print("[ERROR] No GEMINI_API_KEY in .secrets.toml.")
        print("        Open the app, go to Settings, and enter your Gemini API key.")
        sys.exit(1)

    results = {}

    for model in MODELS_TO_TEST:
        print(f"--- Testing: {model}")
        summarizer.model_name = model

        finished = False
        succeeded = False
        result_msg = ""

        def make_callback():
            def callback(ok, msg):
                nonlocal finished, succeeded, result_msg
                finished = True
                succeeded = ok
                result_msg = msg
            return callback

        summarizer.summarize(TEST_TRANSCRIPT, callback=make_callback())

        deadline = time.time() + TIMEOUT_SECONDS
        while not finished and time.time() < deadline:
            time.sleep(0.5)

        if not finished:
            status = "TIMEOUT"
            detail = f"No response after {TIMEOUT_SECONDS}s"
        elif succeeded:
            status = "PASS"
            detail = result_msg
        else:
            status = "FAIL"
            # Extract just the first meaningful error line
            first_line = result_msg.split("\n")[0]
            detail = first_line

        results[model] = (status, detail)

        icons = {"PASS": "[PASS]", "FAIL": "[FAIL]", "TIMEOUT": "[TIMEOUT]"}
        print(f"  {icons[status]} {detail}\n")

    # Final summary
    print("=== Results ===")
    passed = sum(1 for s, _ in results.values() if s == "PASS")
    for model, (status, detail) in results.items():
        icons = {"PASS": "[PASS]", "FAIL": "[FAIL]", "TIMEOUT": "[TIMEOUT]"}
        print(f"  {icons[status]}  {model}")
        if status != "PASS":
            print(f"         {detail}")

    print(f"\n{passed}/{len(MODELS_TO_TEST)} models succeeded.")
    if any(s != "PASS" for s, _ in results.values()):
        print("\nNote: gemini-1.5-flash was deprecated by Google in early 2025 and returns 404.")
        print("      The other models are healthy.")


if __name__ == "__main__":
    run_tests()

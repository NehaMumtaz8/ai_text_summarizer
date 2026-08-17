# =============================================================
#  check_gemini_key.py — standalone Gemini API key diagnostic
#
#  Run this directly (no Flask needed) to find out, in isolation,
#  whether GEMINI_API_KEY in your .env is actually valid:
#
#      python check_gemini_key.py
#
#  It never prints the key itself. Delete this file once you've
#  confirmed the key works — it's a diagnostic tool, not part of
#  the app.
# =============================================================
import os
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")

print("── Gemini API key diagnostic ──")

if not key:
    print("FAIL: GEMINI_API_KEY is not set in your .env file at all.")
    print("      Add a line: GEMINI_API_KEY=your_key_here")
    raise SystemExit(1)

print(f"Key found in .env (length={len(key)}, starts with 'AIza'={key.startswith('AIza')})")

if not key.startswith("AIza") or len(key) < 30:
    print("FAIL: this does not look like a real Google API key.")
    print("      Get a fresh one at https://aistudio.google.com/app/apikey")
    raise SystemExit(1)

import google.generativeai as genai

try:
    genai.configure(api_key=key)
    # list_models is a lightweight call that will surface an invalid-key
    # error immediately, without spending a generation request.
    models = list(genai.list_models())
    print(f"SUCCESS: key is valid — {len(models)} models visible to this key.")
except Exception as e:
    print(f"FAIL: Google rejected this key — {type(e).__name__}: {e}")
    print()
    print("This means the key itself is the problem, not your Flask code.")
    print("Most common causes:")
    print("  1. The key was deleted/regenerated in Google AI Studio since you copied it.")
    print("  2. The key was copied with a missing/extra character.")
    print("  3. The 'Generative Language API' isn't enabled for the")
    print("     Google Cloud project the key belongs to.")
    print()
    print("Fix: generate a new key at https://aistudio.google.com/app/apikey,")
    print("     paste it into .env as GEMINI_API_KEY=<key>, save, and re-run this script.")

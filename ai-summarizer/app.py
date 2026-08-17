# =============================================================
#  app.py  —  AI Summarizer Flask Backend
#
#  Stateless AI backend: BART summarization, predefined-Q&A chat,
#  and PDF text extraction only. User accounts, sessions, and
#  history are handled entirely client-side via browser Local
#  Storage — see static/js/storage.js. There is no server-side
#  database. The chatbot no longer calls any external AI API —
#  see chatbot_qa.py.
# =============================================================

from dotenv import load_dotenv
load_dotenv()   # loads .env file first — order matters!

import os
import PyPDF2
from chatbot_qa import get_answer as get_chat_answer   # local predefined chatbot
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from transformers import pipeline
from werkzeug.utils import secure_filename
import torch

# ── App setup ─────────────────────────────────────────────────
app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production-please")

CORS(app, supports_credentials=True, origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "null"
])

# ── Upload configuration ──────────────────────────────────────
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024   # 50 MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ═════════════════════════════════════════════════════════════
#  STORAGE
#  User accounts and history (summaries/quizzes/flashcards/PDF
#  records) are stored entirely in the browser's Local Storage —
#  see static/js/storage.js. There is no server-side database.
#  This Flask backend is stateless: it only does AI processing
#  (BART summarization, Gemini chat, PDF text extraction).
# ═════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════
#  GEMINI SETUP
# ═════════════════════════════════════════════════════════════
#  CHATBOT SETUP
#  Gemini has been fully removed. The chatbot now answers from a
#  predefined, local question/answer knowledge base — see
#  chatbot_qa.py. No API key, no external network call, no cost.
# ═════════════════════════════════════════════════════════════
print("Predefined chatbot loaded (no external AI API, no API key required).")

# ═════════════════════════════════════════════════════════════
#  BART MODEL
#  NOTE: requires transformers==4.57.3 (or any 4.x release).
#  Transformers v5 removed the "summarization" pipeline task,
#  which causes: KeyError: "Unknown task summarization, ...".
#  Fix: pip uninstall -y transformers && pip install "transformers==4.57.3"
# ═════════════════════════════════════════════════════════════
print("Loading facebook/bart-large-cnn …")
device     = 0 if torch.cuda.is_available() else -1
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    device=device
)
print("BART ready!")


# ═════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ═════════════════════════════════════════════════════════════

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_lengths(text, depth):
    word_count   = len(text.split())
    token_approx = int(word_count * 1.3)
    if depth == "concise":
        max_len = min(80,  token_approx - 1)
        min_len = min(30,  max_len - 10)
    elif depth == "bullets":
        max_len = min(200, token_approx - 1)
        min_len = min(80,  max_len - 20)
    else:
        max_len = min(400, token_approx - 1)
        min_len = min(150, max_len - 30)
    min_len = max(10, min(min_len, max_len - 10))
    return max_len, min_len


def extract_text_from_pdf(filepath):
    text_parts = []
    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        if reader.is_encrypted:
            raise ValueError("PDF is password-protected. Please unlock it first.")
        total_pages = len(reader.pages)
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(" ".join(page_text.split()))
            except Exception:
                continue
    full_text = " ".join(text_parts).strip()
    if not full_text:
        raise ValueError("No readable text found. May be a scanned image PDF.")
    return full_text, total_pages


# ═════════════════════════════════════════════════════════════
#  PAGE ROUTES
#  No server-side auth gate anymore — accounts/sessions live in
#  the browser's Local Storage (static/js/storage.js). welcome.html
#  checks Local Storage itself on load and redirects to /login if
#  no user is signed in.
# ═════════════════════════════════════════════════════════════

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/welcome")
def welcome_page():
    return render_template("welcome.html")

@app.route("/index")
def index_page():
    # Public landing page (alias of "/")
    return render_template("index.html")


# ═════════════════════════════════════════════════════════════
#  CORE FEATURE ROUTES
#  Signup, login, logout, and all history (summaries/quizzes/
#  flashcards/PDF records) are handled entirely client-side in
#  Local Storage — see static/js/storage.js. Only the AI
#  processing routes below remain on the Flask backend.
# ═════════════════════════════════════════════════════════════

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field."}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400
    if len(user_message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)."}), 400

    # Predefined, fully local answer — no external AI API, no API key.
    reply = get_chat_answer(user_message)
    return jsonify({"reply": reply})


@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file field. Field must be named 'file'."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are accepted."}), 400

    safe_name = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)

    try:
        file.save(save_path)
    except Exception as e:
        return jsonify({"error": f"Could not save file: {str(e)}"}), 500

    try:
        extracted_text, page_count = extract_text_from_pdf(save_path)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 422
    except Exception as e:
        return jsonify({"error": f"PDF extraction failed: {str(e)}"}), 500
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)

    return jsonify({
        "text":       extracted_text,
        "word_count": len(extracted_text.split()),
        "page_count": page_count,
        "filename":   safe_name
    })


@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field."}), 400

    text  = data["text"].strip()
    depth = data.get("depth", "concise")

    if len(text) < 50:
        return jsonify({"error": "Text too short. Provide at least 50 characters."}), 400

    try:
        max_len, min_len = safe_lengths(text, depth)
        result = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
        summary_text = result[0]["summary_text"]

        if depth == "bullets":
            sentences    = [s.strip() for s in summary_text.split(". ") if s.strip()]
            summary_text = "\n".join(f"• {s}" for s in sentences)

        return jsonify({"summary": summary_text})
    except Exception as e:
        return jsonify({"error": f"Model error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":      "ok",
        "bart_model":  "facebook/bart-large-cnn",
        "chat_mode":   "predefined-qa",   # local Q&A, no external AI API
        "storage":     "localStorage"
    })


# ── Run ───────────────────────────────────────────────────────
if __name__ == "__main__":
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"]   = False   # True in production (HTTPS)
    # use_reloader=False: Werkzeug's auto-reloader (which restarts the process
    # on file changes) can crash on Windows with "OSError: [WinError 10038]"
    # when heavy libraries like torch are loaded. debug=True is kept, so the
    # interactive debugger/tracebacks still work — you just need to manually
    # restart `python app.py` after editing code instead of it auto-reloading.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
    
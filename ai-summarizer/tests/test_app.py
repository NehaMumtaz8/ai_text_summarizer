"""
Backend tests for app.py — now a stateless AI backend (BART /
predefined-Q&A chat / PDF extraction). Auth and history live
client-side; see test_storage.js for those.

Run with:  pytest tests/ -v
"""


def test_app_starts_and_imports(app):
    assert app is not None


def test_index_route_serves_landing_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"AI" in res.data


def test_index_alias_route(client):
    res = client.get("/index")
    assert res.status_code == 200


def test_login_route_serves_login_page(client):
    res = client.get("/login")
    assert res.status_code == 200
    assert b"Welcome Back" in res.data


def test_signup_route_serves_signup_page(client):
    res = client.get("/signup")
    assert res.status_code == 200
    assert b"Signup AI Summarizer" in res.data


def test_welcome_route_serves_dashboard_without_server_side_auth(client):
    # No more server-side session gate — the page itself checks
    # Local Storage client-side and redirects if no user is found.
    res = client.get("/welcome")
    assert res.status_code == 200


def test_welcome_page_loads_storage_js(client):
    res = client.get("/welcome")
    assert b"/static/js/storage.js" in res.data


def test_login_page_loads_storage_js(client):
    res = client.get("/login")
    assert b"/static/js/storage.js" in res.data


def test_signup_page_loads_storage_js(client):
    res = client.get("/signup")
    assert b"/static/js/storage.js" in res.data


def test_storage_js_is_served_as_static_file(client):
    res = client.get("/static/js/storage.js")
    assert res.status_code == 200
    assert b"signupUser" in res.data


def test_no_auth_or_history_routes_remain(client):
    # These MongoDB-backed routes have been fully removed.
    for path in ["/auth/signup", "/auth/login", "/auth/logout", "/auth/me"]:
        res = client.get(path)
        assert res.status_code == 404
    for path in ["/history/summaries", "/history/quizzes", "/history/flashcards", "/history/pdfs"]:
        res = client.get(path)
        assert res.status_code == 404


# ── AI feature routes (stubbed BART, real predefined chat, real Flask logic) ──

def test_summarize_missing_text_field(client):
    res = client.post("/summarize", json={})
    assert res.status_code == 400


def test_summarize_text_too_short(client):
    res = client.post("/summarize", json={"text": "short"})
    assert res.status_code == 400


def test_summarize_success_with_stubbed_bart(client):
    long_text = "This is a sufficiently long piece of text. " * 5
    res = client.post("/summarize", json={"text": long_text, "depth": "concise"})
    assert res.status_code == 200
    assert res.get_json()["summary"] == "stubbed summary"


def test_chat_missing_message_field(client):
    res = client.post("/chat", json={})
    assert res.status_code == 400


def test_chat_success_with_predefined_greeting(client):
    # No Gemini/external API involved anymore — this hits the real
    # local chatbot_qa.get_answer() logic.
    res = client.post("/chat", json={"message": "hello"})
    assert res.status_code == 200
    assert "Welcome to AI Summarizer" in res.get_json()["reply"]


def test_chat_unsupported_question_gets_friendly_fallback(client):
    res = client.post("/chat", json={"message": "xyzzy plugh unrelated gibberish"})
    assert res.status_code == 200
    assert "suggested questions" in res.get_json()["reply"]


def test_chat_never_requires_gemini_api_key(client):
    # No GEMINI_API_KEY is set anywhere in this test run (see conftest.py),
    # and /chat must still work — proving the chatbot has no external
    # AI dependency.
    res = client.post("/chat", json={"message": "what is bart?"})
    assert res.status_code == 200
    assert "BART" in res.get_json()["reply"]


def test_upload_pdf_no_file(client):
    res = client.post("/upload-pdf", data={})
    assert res.status_code == 400


# ── Health check ──────────────────────────────────────────────────

def test_health_endpoint_no_longer_reports_mongo(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["storage"] == "localStorage"
    assert "mongo_ready" not in data

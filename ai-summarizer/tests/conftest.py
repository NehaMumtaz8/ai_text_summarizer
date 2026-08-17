"""
Test harness for app.py.

app.py still imports heavy ML dependencies (torch, transformers) at
module load time. Those aren't available in a CI-style test
environment, so we stub them out BEFORE importing app.py. This lets us
exercise the real Flask routes untouched.

The chatbot no longer uses Gemini or any external AI API — it's a
local predefined Q&A engine (chatbot_qa.py), so no stubbing or API key
is needed for it.

There is no MongoDB to fake either — app.py is a stateless AI backend
(BART / predefined chat / PDF extraction only). Accounts and history
live in the browser via static/js/storage.js, which is tested
separately in tests/test_storage.js (a plain Node script).
"""
import sys
import types
import pytest


@pytest.fixture
def app(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
    sys.modules.setdefault("torch", fake_torch)

    fake_transformers = types.ModuleType("transformers")
    fake_transformers.pipeline = lambda *a, **k: (lambda text, **kw: [{"summary_text": "stubbed summary"}])
    sys.modules.setdefault("transformers", fake_transformers)

    monkeypatch.setenv("SECRET_KEY", "test-secret")

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

    import importlib
    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
        app_module = sys.modules["app"]
    else:
        app_module = importlib.import_module("app")

    app_module.app.config.update(TESTING=True)
    yield app_module.app


@pytest.fixture
def client(app):
    return app.test_client()

import os
import tempfile

os.environ["TICKETS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)  # force fallback so tests are offline

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_create_and_fetch_ticket():
    r = client.post("/tickets", json={"customer": "Ada", "message": "I was charged twice, need a refund ASAP"})
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "billing"
    assert body["priority"] == "high"
    assert client.get(f"/tickets/{body['id']}").json()["customer"] == "Ada"


def test_filter_and_404():
    client.post("/tickets", json={"customer": "Bo", "message": "The app keeps crashing"})
    assert all(t["category"] == "technical" for t in client.get("/tickets?category=technical").json())
    assert client.get("/tickets/9999").status_code == 404


def test_validation():
    assert client.post("/tickets", json={"customer": "", "message": "hi"}).status_code == 422

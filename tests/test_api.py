"""API tests. Claude is replaced with a fake, so these run free and offline."""

import os
import tempfile

os.environ["PROMPT_COACH_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from backend import coach, main  # noqa: E402

client = TestClient(main.app)

FAKE_REPORT = coach.CoachReport(
    overall_score=42,
    summary="Clear goal, but missing audience and format.",
    criteria=[coach.Criterion(name="Clarity", score=7, feedback="Task is clear.")],
    improved_prompt="Write a 600-word blog post for [your audience] about productivity.",
    key_changes=["Added length and audience."],
)


def test_coach_saves_to_history(monkeypatch):
    monkeypatch.setattr(coach, "coach_prompt", lambda prompt: FAKE_REPORT)

    res = client.post("/api/coach", json={"prompt": "write a blog post"})
    assert res.status_code == 200
    assert res.json()["report"]["overall_score"] == 42

    history = client.get("/api/history").json()
    assert history[0]["original_prompt"] == "write a blog post"


def test_empty_prompt_is_rejected():
    res = client.post("/api/coach", json={"prompt": ""})
    assert res.status_code == 422


def test_claude_errors_become_friendly_messages(monkeypatch):
    def boom(prompt):
        raise coach.CoachError("Your API key was rejected.")

    monkeypatch.setattr(coach, "coach_prompt", boom)
    res = client.post("/api/coach", json={"prompt": "hi"})
    assert res.status_code == 502
    assert "API key" in res.json()["detail"]


def test_delete_history(monkeypatch):
    monkeypatch.setattr(coach, "coach_prompt", lambda prompt: FAKE_REPORT)
    session_id = client.post("/api/coach", json={"prompt": "to delete"}).json()["id"]

    assert client.delete(f"/api/history/{session_id}").status_code == 200
    assert client.delete(f"/api/history/{session_id}").status_code == 404

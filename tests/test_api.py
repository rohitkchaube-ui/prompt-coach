"""API tests. Claude is replaced with a fake, so these run free and offline."""

import os
import tempfile

import pytest

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
    recommended_model="claude-sonnet-5-5",
    recommendation_reason="A standard writing task; Sonnet handles it well for less.",
)
FAKE_USAGE = coach.Usage(model="claude-opus-5-5", input_tokens=900, output_tokens=1200, cost_usd=0.0276)


@pytest.fixture
def fake_coach(monkeypatch):
    monkeypatch.setattr(coach, "coach_prompt", lambda prompt: (FAKE_REPORT, FAKE_USAGE))


def test_coach_returns_usage_and_saves_to_history(fake_coach):
    res = client.post("/api/coach", json={"prompt": "write a blog post"})
    assert res.status_code == 200
    body = res.json()
    assert body["report"]["overall_score"] == 42
    assert body["report"]["recommended_model"] == "claude-sonnet-5-5"
    assert body["usage"]["cost_usd"] == pytest.approx(0.0276)

    latest = client.get("/api/history").json()[0]
    assert latest["original_prompt"] == "write a blog post"
    assert latest["usage"]["output_tokens"] == 1200
    assert "usage" not in latest["report"]


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


def test_delete_history(fake_coach):
    session_id = client.post("/api/coach", json={"prompt": "to delete"}).json()["id"]

    assert client.delete(f"/api/history/{session_id}").status_code == 200
    assert client.delete(f"/api/history/{session_id}").status_code == 404


def test_compare_runs_both_prompts_on_chosen_model(monkeypatch):
    seen = []

    def fake_run(prompt, model):
        seen.append(model)
        return f"answer to: {prompt}", coach.Usage(
            model=model, input_tokens=10, output_tokens=20, cost_usd=0.001
        )

    monkeypatch.setattr(coach, "run_prompt", fake_run)
    res = client.post(
        "/api/compare",
        json={"original": "a", "improved": "b", "model": "claude-haiku-5-5"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["original"]["text"] == "answer to: a"
    assert body["improved"]["usage"]["model"] == "claude-haiku-5-5"
    assert seen == ["claude-haiku-5-5", "claude-haiku-5-5"]


def test_compare_rejects_unknown_model():
    res = client.post("/api/compare", json={"original": "a", "improved": "b", "model": "gpt-9"})
    assert res.status_code == 422


def test_models_endpoint_lists_prices():
    models = client.get("/api/models").json()
    ids = [m["id"] for m in models]
    assert "claude-sonnet-5-5" in ids
    assert all(m["input"] > 0 and m["output"] > 0 for m in models)


def test_cost_calculation():
    # Opus 5.5: $4 in / $20 out per million tokens
    assert coach.calculate_cost("claude-opus-5-5", 1_000_000, 0) == pytest.approx(4.0)
    assert coach.calculate_cost("claude-opus-5-5", 1000, 1000) == pytest.approx(0.024)
    # Haiku 5.5 charges more once the prompt is over 100K tokens
    assert coach.calculate_cost("claude-haiku-5-5", 200_000, 0) == pytest.approx(0.10)
    # Unknown model (e.g. an unexpected fallback) costs 0 rather than crashing
    assert coach.calculate_cost("some-other-model", 1000, 1000) == 0.0

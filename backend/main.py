"""FastAPI app: JSON API under /api, and the frontend served from /."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()  # must run before the Claude client is created

from . import coach, db  # noqa: E402

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Prompt Coach")
db.init_db()


class PromptIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)


class CompareIn(BaseModel):
    original: str = Field(min_length=1, max_length=20000)
    improved: str = Field(min_length=1, max_length=20000)
    model: coach.ModelId


@app.get("/api/models")
def models_endpoint():
    """Model list with prices, for the model picker in the frontend."""
    return [{"id": mid, **info} for mid, info in coach.MODELS.items()]


@app.post("/api/coach")
def coach_endpoint(body: PromptIn):
    try:
        report, usage = coach.coach_prompt(body.prompt)
    except coach.CoachError as e:
        raise HTTPException(status_code=502, detail=str(e))
    report, usage = report.model_dump(), usage.model_dump()
    session_id = db.save_session(body.prompt, report, usage)
    return {"id": session_id, "report": report, "usage": usage}


@app.post("/api/compare")
def compare_endpoint(body: CompareIn):
    """Run both prompts at the same time on the chosen model and return both answers."""
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            original = pool.submit(coach.run_prompt, body.original, body.model)
            improved = pool.submit(coach.run_prompt, body.improved, body.model)
            results = {"original": original.result(), "improved": improved.result()}
    except coach.CoachError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        name: {"text": text, "usage": usage.model_dump()}
        for name, (text, usage) in results.items()
    }


@app.get("/api/history")
def history_endpoint():
    return db.list_sessions()


@app.delete("/api/history/{session_id}")
def delete_history_endpoint(session_id: int):
    if not db.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


# Mounted last so it doesn't shadow the /api routes.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

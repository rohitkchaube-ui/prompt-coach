# Prompt Coach — notes for Claude Code

## What this is
A learning project: a FastAPI + vanilla JS app that grades and improves prompts using the Claude API.
The owner is using it to get comfortable with Claude Code and GitHub, so explain git and GitHub steps briefly when doing them.

## Commands
- Run the app: `uvicorn backend.main:app --reload` (then http://localhost:8000)
- Run tests: `pytest`

## Layout
- `backend/coach.py` — the only file that calls the Claude API (model, prompts, error handling)
- `backend/db.py` — SQLite storage
- `backend/main.py` — FastAPI routes; serves `frontend/` at `/`
- `frontend/` — no build step; plain HTML/CSS/JS
- `tests/` — tests mock `coach.coach_prompt`, so they never call the real API

## Conventions
- Keep Claude API calls inside `backend/coach.py`.
- Never commit `.env` or `*.db`.
- Add or update a test in `tests/` when changing an API route.
- Small, focused commits with clear messages; work on a branch for each new feature.

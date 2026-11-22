# Prompt Coach

[![Tests](https://github.com/rohitkchaube-ui/prompt-coach/actions/workflows/tests.yml/badge.svg)](https://github.com/rohitkchaube-ui/prompt-coach/actions/workflows/tests.yml)

A small full-stack app that helps you write better prompts for Claude.

1. **Write** a prompt you plan to use.
2. **Get coached**: Claude scores it on clarity, context, specificity, output format and examples, and explains each score.
3. **See the improved version**, plus a list of what changed and why.
4. **Compare**: run the original and improved prompts side by side and see how the answers differ.
5. **Track progress**: every session is saved to a local history.

## Stack

| Layer    | Tech                                   |
|----------|----------------------------------------|
| Frontend | Plain HTML, CSS and JavaScript (`frontend/`) |
| Backend  | Python + FastAPI (`backend/`)          |
| AI       | Claude API via the `anthropic` SDK (`backend/coach.py`) |
| Storage  | SQLite (`prompt_coach.db`, created automatically) |

## Quick start

**You need:** [Python 3.10 or newer](https://www.python.org/downloads/) (on Windows, tick *"Add python.exe to PATH"* during install) and a Claude API key from <https://console.anthropic.com/settings/keys>. API usage is billed to your own key; a coaching run typically costs a few cents.

1. **Download** this project: click the green **Code** button → **Download ZIP**, then unzip it. (Or `git clone` it.)
2. **Start it:**
   - **Windows:** double-click `run.bat`
   - **macOS / Linux:** open a terminal in the folder and run `sh run.sh`
3. The first time, it sets itself up (about a minute) and asks for your API key. Paste it and press Enter; it's saved only on your computer, in `.env`.
4. Your browser opens Prompt Coach. To stop it, press `Ctrl+C` in the terminal window.

Next time, just run `run.bat` / `sh run.sh` again; it starts in seconds.

## For developers

```bash
pip install -r requirements.txt
cp .env.example .env              # then paste your API key into .env
uvicorn backend.main:app --reload # auto-restarts when you edit code
```

Open <http://localhost:8000>. Press `Ctrl+Enter` in the text box to submit.

## Test

```bash
pytest
```

The tests replace Claude with a fake, so they cost nothing and need no API key.

## API

| Method | Path                 | What it does |
|--------|----------------------|--------------|
| POST   | `/api/coach`         | `{prompt}` → score, feedback and improved prompt (saved to history) |
| POST   | `/api/compare`       | `{original, improved, model}` → both prompts' answers with token usage and cost |
| GET    | `/api/models`        | Available models and their prices |
| GET    | `/api/history`       | Past coaching sessions |
| DELETE | `/api/history/{id}`  | Delete one session |

Interactive API docs: <http://localhost:8000/docs>

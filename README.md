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

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your API key into .env
```

Get an API key at <https://console.anthropic.com/settings/keys>.

## Run

```bash
uvicorn backend.main:app --reload
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
| POST   | `/api/compare`       | `{original, improved}` → both prompts' answers |
| GET    | `/api/history`       | Past coaching sessions |
| DELETE | `/api/history/{id}`  | Delete one session |

Interactive API docs: <http://localhost:8000/docs>

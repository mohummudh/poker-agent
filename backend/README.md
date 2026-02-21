# Backend (FastAPI)

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Environment

- `GEMINI_API_KEY` (optional for live LLM opponent)
- `GEMINI_MODEL` (default: `gemini-1.5-flash`)
- `LLM_TIMEOUT_MS` (default: `5000`)
- `LLM_RETRIES` (default: `1`)

If `GEMINI_API_KEY` is not set or Gemini fails, the server uses a deterministic fallback policy.

## Tests

```bash
pytest
```

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
- `LLM_TIMEOUT_MS` (default: `2500`)
- `LLM_RETRIES` (default: `0`)
- `LLM_CACHE_SIZE` (default: `512`)
- `MAX_POLICY_CALLS_PER_REQUEST` (default: `1`)
- `LIVE_FEED_LIMIT` (default: `80`)

If `GEMINI_API_KEY` is not set or Gemini fails, the server uses a deterministic fallback policy.

For lowest possible latency, use:

```bash
export LLM_TIMEOUT_MS=1200
export LLM_RETRIES=0
export MAX_POLICY_CALLS_PER_REQUEST=1
```

## Tests

```bash
pytest
```

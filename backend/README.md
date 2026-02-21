# Backend (FastAPI)

## Run

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Production-style local run:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
```

Alternative server (optional):

```bash
granian --interface asgi app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

## Environment

- `GEMINI_API_KEY` (optional for live LLM opponent)
- `GEMINI_MODEL` (default: `gemini-2.5-flash`)
- `LLM_TIMEOUT_MS` (default: `2500`)
- `LLM_RETRIES` (default: `0`)
- `LLM_CACHE_SIZE` (default: `512`)
- `MAX_POLICY_CALLS_PER_REQUEST` (default: `1`)
- `LIVE_FEED_LIMIT` (default: `80`)
- `SMALL_BLIND` (default: `1`)
- `BIG_BLIND` (default: `2`)
- `STARTING_STACK` (default: `200`)

If `GEMINI_API_KEY` is not set or Gemini fails, the server uses a deterministic fallback policy.
The backend auto-loads both `backend/.env` and project-root `.env` on startup.

Performance notes:
- HTTP handlers and LLM calls run async (`httpx.AsyncClient`) to avoid thread blocking.
- If `orjson` is installed, API responses use `ORJSONResponse` automatically.
- Showdown eval prefers `phevaluator`, then `treys`, then pure-Python fallback.

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

# Pixel Poker Duel

Heads-up no-limit Texas Hold'em where a human plays against an LLM-driven opponent.

## Run backend

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# optional performance tuning:
# export LLM_TIMEOUT_MS=2500
# export LLM_RETRIES=0
# export LLM_CACHE_SIZE=512
# export MAX_POLICY_CALLS_PER_REQUEST=1
# export LIVE_FEED_LIMIT=80
uvicorn app.main:app --reload --port 8000
```

The backend auto-loads `backend/.env` (and root `.env` if present).

Production-style local run (multi-worker):

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
```

Alternative high-performance server (optional install):

```bash
granian --interface asgi app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server proxies `/api` to `http://127.0.0.1:8000`.
WebSocket traffic under `/api/ws/*` is proxied too.

Optional local font files for zero-network font loading:

- `frontend/public/fonts/press-start-2p.woff2`
- `frontend/public/fonts/vt323.woff2`

## Tests

```bash
pytest -q backend/tests
npm --prefix frontend run test
```

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

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server proxies `/api` to `http://127.0.0.1:8000`.

## Tests

```bash
pytest -q backend/tests
npm --prefix frontend run test
```

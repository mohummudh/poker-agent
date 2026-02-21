# Pixel Poker Duel

Heads-up no-limit Texas Hold'em where a human plays against an LLM-driven opponent.

## Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

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

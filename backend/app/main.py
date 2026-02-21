from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .engine import InvalidActionError, SessionFlowError
from .models import ActionResolutionModel, HandReplayModel, HandSummaryModel, HumanActionRequestModel, SessionStateModel
from .session_manager import SessionManager, SessionNotFoundError

app = FastAPI(title="Pixel Poker API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SessionManager()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sessions", response_model=SessionStateModel)
def create_session() -> SessionStateModel:
    return manager.create_session()


@app.get("/api/sessions/{session_id}", response_model=SessionStateModel)
def get_session(session_id: str) -> SessionStateModel:
    try:
        return manager.get_state(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/actions", response_model=ActionResolutionModel)
def apply_action(session_id: str, payload: HumanActionRequestModel) -> ActionResolutionModel:
    try:
        return manager.apply_action(session_id, payload)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidActionError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "legalActions": [item.model_dump(by_alias=True) for item in exc.legal_actions],
            },
        ) from exc
    except SessionFlowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/next-hand", response_model=SessionStateModel)
def next_hand(session_id: str) -> SessionStateModel:
    try:
        return manager.next_hand(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionFlowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/rebuy", response_model=SessionStateModel)
def rebuy(session_id: str) -> SessionStateModel:
    try:
        return manager.rebuy(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionFlowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/hands", response_model=list[HandSummaryModel])
def list_hands(session_id: str) -> list[HandSummaryModel]:
    try:
        return manager.list_hands(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/hands/{hand_id}/replay", response_model=HandReplayModel)
def get_replay(session_id: str, hand_id: str) -> HandReplayModel:
    try:
        return manager.get_replay(session_id, hand_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

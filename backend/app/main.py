from __future__ import annotations

import importlib.util
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from pydantic import ValidationError

from .config import load_environment
from .engine import InvalidActionError, SessionFlowError
from .models import ActionResolutionModel, HandReplayModel, HandSummaryModel, HumanActionRequestModel, SessionStateModel
from .session_manager import SessionManager, SessionNotFoundError

load_environment()

DefaultResponseClass = ORJSONResponse if importlib.util.find_spec("orjson") else JSONResponse
manager = SessionManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await manager.aclose()


app = FastAPI(
    title="Pixel Poker API",
    version="0.1.0",
    default_response_class=DefaultResponseClass,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sessions", response_model=SessionStateModel)
async def create_session() -> SessionStateModel:
    return await manager.create_session()


@app.get("/api/sessions/{session_id}", response_model=SessionStateModel)
async def get_session(session_id: str) -> SessionStateModel:
    try:
        return await manager.get_state(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/actions", response_model=ActionResolutionModel)
async def apply_action(session_id: str, payload: HumanActionRequestModel) -> ActionResolutionModel:
    try:
        return await manager.apply_action(session_id, payload)
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
async def next_hand(session_id: str) -> SessionStateModel:
    try:
        return await manager.next_hand(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionFlowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/rebuy", response_model=SessionStateModel)
async def rebuy(session_id: str) -> SessionStateModel:
    try:
        return await manager.rebuy(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionFlowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/hands", response_model=list[HandSummaryModel])
async def list_hands(session_id: str) -> list[HandSummaryModel]:
    try:
        return await manager.list_hands(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/hands/{hand_id}/replay", response_model=HandReplayModel)
async def get_replay(session_id: str, hand_id: str) -> HandReplayModel:
    try:
        return await manager.get_replay(session_id, hand_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _ws_error_payload(request_id: str, status: int, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "error",
        "requestId": request_id,
        "status": status,
        "message": message,
    }
    if extra:
        payload.update(extra)
    return payload


@app.websocket("/api/ws/sessions/{session_id}")
async def session_socket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        initial_state = await manager.get_state(session_id)
    except SessionNotFoundError as exc:
        await websocket.send_json(_ws_error_payload(request_id="", status=404, message=str(exc)))
        await websocket.close(code=4404)
        return

    await websocket.send_json(
        {
            "type": "session_state",
            "requestId": "",
            "payload": initial_state.model_dump(by_alias=True),
        }
    )

    while True:
        try:
            raw_message = await websocket.receive_json()
        except WebSocketDisconnect:
            return
        except Exception:
            await websocket.send_json(_ws_error_payload(request_id="", status=400, message="Malformed websocket JSON payload."))
            continue

        if not isinstance(raw_message, dict):
            await websocket.send_json(_ws_error_payload(request_id="", status=400, message="Websocket message must be a JSON object."))
            continue

        request_id = str(raw_message.get("requestId", ""))
        op = str(raw_message.get("op", "")).strip().lower()

        try:
            if op == "ping":
                await websocket.send_json({"type": "pong", "requestId": request_id})
                continue

            if op == "get_state":
                state = await manager.get_state(session_id)
                await websocket.send_json(
                    {
                        "type": "session_state",
                        "requestId": request_id,
                        "payload": state.model_dump(by_alias=True),
                    }
                )
                continue

            if op == "action":
                action_payload = HumanActionRequestModel.model_validate(
                    {
                        "actionType": raw_message.get("actionType"),
                        "amount": raw_message.get("amount"),
                    }
                )
                result = await manager.apply_action(session_id, action_payload)
                await websocket.send_json(
                    {
                        "type": "action_resolution",
                        "requestId": request_id,
                        "payload": result.model_dump(by_alias=True),
                    }
                )
                continue

            if op == "next_hand":
                state = await manager.next_hand(session_id)
                await websocket.send_json(
                    {
                        "type": "session_state",
                        "requestId": request_id,
                        "payload": state.model_dump(by_alias=True),
                    }
                )
                continue

            if op == "rebuy":
                state = await manager.rebuy(session_id)
                await websocket.send_json(
                    {
                        "type": "session_state",
                        "requestId": request_id,
                        "payload": state.model_dump(by_alias=True),
                    }
                )
                continue

            await websocket.send_json(
                _ws_error_payload(request_id=request_id, status=400, message=f"Unsupported websocket op: {op}")
            )
        except SessionNotFoundError as exc:
            await websocket.send_json(_ws_error_payload(request_id=request_id, status=404, message=str(exc)))
        except ValidationError as exc:
            await websocket.send_json(_ws_error_payload(request_id=request_id, status=422, message="Invalid action payload.", extra={"detail": exc.errors()}))
        except InvalidActionError as exc:
            await websocket.send_json(
                _ws_error_payload(
                    request_id=request_id,
                    status=422,
                    message=str(exc),
                    extra={"legalActions": [item.model_dump(by_alias=True) for item in exc.legal_actions]},
                )
            )
        except SessionFlowError as exc:
            await websocket.send_json(_ws_error_payload(request_id=request_id, status=409, message=str(exc)))

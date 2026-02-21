from __future__ import annotations

import threading
import uuid

from .engine import HeadsUpSession, InvalidActionError, SessionFlowError
from .models import ActionResolutionModel, HandReplayModel, HandSummaryModel, HumanActionRequestModel, SessionStateModel
from .opponent import GeminiPolicy


class SessionNotFoundError(KeyError):
    pass


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, HeadsUpSession] = {}
        self._lock = threading.RLock()

    def create_session(self) -> SessionStateModel:
        with self._lock:
            session_id = uuid.uuid4().hex[:12]
            session = HeadsUpSession(session_id=session_id, opponent_policy=GeminiPolicy.from_env())
            self._sessions[session_id] = session
            return session.get_state()

    def get_state(self, session_id: str) -> SessionStateModel:
        with self._lock:
            return self._get_session(session_id).get_state()

    def apply_action(self, session_id: str, payload: HumanActionRequestModel) -> ActionResolutionModel:
        with self._lock:
            session = self._get_session(session_id)
            events = session.process_human_action(payload.action_type, payload.amount)
            state = session.get_state()
            return ActionResolutionModel(
                session_state=state,
                applied_events=events,
                hand_complete=state.status in {"hand_complete", "session_complete"},
            )

    def next_hand(self, session_id: str) -> SessionStateModel:
        with self._lock:
            session = self._get_session(session_id)
            return session.start_next_hand()

    def rebuy(self, session_id: str, stack_amount: int = 200) -> SessionStateModel:
        with self._lock:
            session = self._get_session(session_id)
            return session.rebuy_busted_and_start(stack_amount=stack_amount)

    def list_hands(self, session_id: str) -> list[HandSummaryModel]:
        with self._lock:
            session = self._get_session(session_id)
            return session.list_hands()

    def get_replay(self, session_id: str, hand_id: str) -> HandReplayModel:
        with self._lock:
            session = self._get_session(session_id)
            return session.get_replay(hand_id)

    def _get_session(self, session_id: str) -> HeadsUpSession:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        return session


__all__ = [
    "InvalidActionError",
    "SessionFlowError",
    "SessionManager",
    "SessionNotFoundError",
]

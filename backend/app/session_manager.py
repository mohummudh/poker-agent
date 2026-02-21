from __future__ import annotations

import asyncio
import inspect
import os
import uuid

from .engine import HeadsUpSession, InvalidActionError, SessionFlowError
from .models import ActionResolutionModel, HandReplayModel, HandSummaryModel, HumanActionRequestModel, SessionStateModel
from .opponent import GeminiPolicy


class SessionNotFoundError(KeyError):
    pass


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, HeadsUpSession] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
        self._opponent_policy = GeminiPolicy.from_env()
        self._small_blind = int(os.getenv("SMALL_BLIND", "1"))
        self._big_blind = int(os.getenv("BIG_BLIND", "2"))
        self._starting_stack = int(os.getenv("STARTING_STACK", "200"))
        self._live_feed_limit = int(os.getenv("LIVE_FEED_LIMIT", "80"))
        self._max_policy_calls_per_request = int(os.getenv("MAX_POLICY_CALLS_PER_REQUEST", "1"))

    async def aclose(self) -> None:
        close_method = getattr(self._opponent_policy, "aclose", None)
        if close_method is None:
            return
        result = close_method()
        if inspect.isawaitable(result):
            await result

    async def create_session(self) -> SessionStateModel:
        async with self._lock:
            session_id = uuid.uuid4().hex[:12]
            session = HeadsUpSession(
                session_id=session_id,
                opponent_policy=self._opponent_policy,
                small_blind=self._small_blind,
                big_blind=self._big_blind,
                starting_stacks=self._starting_stack,
                live_feed_limit=self._live_feed_limit,
                max_policy_calls_per_request=self._max_policy_calls_per_request,
            )
            self._sessions[session_id] = session
            self._session_locks[session_id] = asyncio.Lock()
        return session.get_state()

    async def get_state(self, session_id: str) -> SessionStateModel:
        session, lock = await self._get_session_entry(session_id)
        async with lock:
            return session.get_state()

    async def apply_action(self, session_id: str, payload: HumanActionRequestModel) -> ActionResolutionModel:
        session, lock = await self._get_session_entry(session_id)
        async with lock:
            events = await session.process_human_action(payload.action_type, payload.amount)
            state = session.get_state()
            return ActionResolutionModel(
                session_state=state,
                applied_events=events,
                hand_complete=state.status in {"hand_complete", "session_complete"},
            )

    async def next_hand(self, session_id: str) -> SessionStateModel:
        session, lock = await self._get_session_entry(session_id)
        async with lock:
            return await session.start_next_hand()

    async def rebuy(self, session_id: str, stack_amount: int = 200) -> SessionStateModel:
        session, lock = await self._get_session_entry(session_id)
        async with lock:
            return await session.rebuy_busted_and_start(stack_amount=stack_amount)

    async def list_hands(self, session_id: str) -> list[HandSummaryModel]:
        session, lock = await self._get_session_entry(session_id)
        async with lock:
            return session.list_hands()

    async def get_replay(self, session_id: str, hand_id: str) -> HandReplayModel:
        session, lock = await self._get_session_entry(session_id)
        async with lock:
            return session.get_replay(hand_id)

    async def _get_session_entry(self, session_id: str) -> tuple[HeadsUpSession, asyncio.Lock]:
        async with self._lock:
            session = self._get_session(session_id)
            lock = self._session_locks.get(session_id)
            if lock is None:
                lock = asyncio.Lock()
                self._session_locks[session_id] = lock
            return session, lock

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

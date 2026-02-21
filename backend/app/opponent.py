from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)


def _normalize_api_key(raw: str | None) -> str | None:
    if raw is None:
        return None

    value = raw.strip()
    if not value:
        return None

    if value.lower() in {
        "your_gemini_api_key_here",
        "replace_with_gemini_key",
        "__replace_me__",
        "changeme",
    }:
        return None

    return value


@dataclass(frozen=True)
class ActionDecision:
    action_type: str
    amount: int | None = None


class OpponentPolicy(Protocol):
    async def decide_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> ActionDecision:
        ...


class DeterministicPolicy:
    """Safe fallback policy that always returns a legal action preference order."""

    async def decide_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> ActionDecision:
        del game_view
        by_type = {item["type"]: item for item in legal_actions}

        if "check" in by_type:
            return ActionDecision(action_type="check")
        if "call" in by_type:
            return ActionDecision(action_type="call")
        if "fold" in by_type:
            return ActionDecision(action_type="fold")
        if "bet" in by_type:
            return ActionDecision(action_type="bet", amount=by_type["bet"].get("min_amount"))
        if "raise" in by_type:
            return ActionDecision(action_type="raise", amount=by_type["raise"].get("min_amount"))
        if "all_in" in by_type:
            return ActionDecision(action_type="all_in", amount=by_type["all_in"].get("max_amount"))

        raise RuntimeError("No legal actions available for fallback policy.")


class GeminiPolicy:
    """Gemini-backed policy with strict JSON output and deterministic fallback."""

    _SYSTEM_PROMPT = (
        "You are a heads-up no-limit Texas Hold'em bot.\n"
        "Return JSON only with schema: "
        '{"action_type":"fold|check|call|bet|raise|all_in","amount":<int optional>}.\n'
        "Choose from legal_actions only."
    )

    def __init__(
        self,
        api_key: str | None,
        model: str,
        timeout_ms: int,
        retries: int = 0,
        cache_size: int = 512,
        fallback: OpponentPolicy | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = max(0.5, timeout_ms / 1000.0)
        self.retries = max(0, retries)
        self.cache_size = max(0, cache_size)
        self.fallback = fallback or DeterministicPolicy()
        self._decision_cache: OrderedDict[str, ActionDecision] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            limits=httpx.Limits(max_connections=64, max_keepalive_connections=32),
            headers={"Content-Type": "application/json"},
            http2=False,
        )

    @classmethod
    def from_env(cls) -> "GeminiPolicy":
        api_key = _normalize_api_key(os.getenv("GEMINI_API_KEY"))
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        timeout_ms = int(os.getenv("LLM_TIMEOUT_MS", "2500"))
        retries = int(os.getenv("LLM_RETRIES", "0"))
        cache_size = int(os.getenv("LLM_CACHE_SIZE", "512"))
        return cls(api_key=api_key, model=model, timeout_ms=timeout_ms, retries=retries, cache_size=cache_size)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def decide_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> ActionDecision:
        fast = self._fast_path_decision(legal_actions)
        if fast:
            return fast

        if not self.api_key:
            return await self.fallback.decide_action(game_view, legal_actions)

        cache_key = self._decision_cache_key(game_view, legal_actions)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        for attempt in range(self.retries + 1):
            try:
                response_text = await self._request_action(game_view, legal_actions)
                parsed = self._parse_json_response(response_text)
                action_type = str(parsed.get("action_type", "")).strip().lower()
                amount = parsed.get("amount")
                if isinstance(amount, float):
                    amount = int(amount)
                if amount is not None and not isinstance(amount, int):
                    amount = None
                if action_type:
                    decision = ActionDecision(action_type=action_type, amount=amount)
                    self._cache_put(cache_key, decision)
                    return decision
            except Exception as exc:  # pragma: no cover - network errors vary by environment
                logger.warning("Gemini decision attempt %s failed: %s", attempt + 1, exc)

        return await self.fallback.decide_action(game_view, legal_actions)

    async def _request_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> str:
        if not self.api_key:
            raise RuntimeError("Gemini API key missing.")

        compact_state = {
            "hand": game_view.get("hand_id"),
            "street": game_view.get("street"),
            "pot": game_view.get("pot"),
            "board": game_view.get("board"),
            "hole": game_view.get("opponent_hole_cards"),
            "stacks": game_view.get("stacks"),
            "to_call": game_view.get("to_call"),
        }
        prompt = (
            f"{self._SYSTEM_PROMPT}\n\n"
            f"state={json.dumps(compact_state, separators=(',', ':'))}\n"
            f"legal_actions={json.dumps(legal_actions, separators=(',', ':'))}"
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "maxOutputTokens": 32,
            },
        }

        model = self.model.replace("/", "%2F")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        response = await self._http.post(url, json=payload)
        response.raise_for_status()

        parsed = response.json()
        text = (
            parsed.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        if not text:
            raise RuntimeError("Gemini response did not include text content.")
        return text

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.strip("`")
            if clean.lower().startswith("json"):
                clean = clean[4:].strip()

        if clean.startswith("{") and clean.endswith("}"):
            return json.loads(clean)

        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end > start:
            return json.loads(clean[start : end + 1])

        raise ValueError("No JSON object found in Gemini response.")

    def _decision_cache_key(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> str:
        raw = json.dumps(
            {"gv": game_view, "la": legal_actions},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.blake2b(raw, digest_size=16).hexdigest()

    def _cache_get(self, key: str) -> ActionDecision | None:
        if self.cache_size <= 0:
            return None
        with self._cache_lock:
            decision = self._decision_cache.get(key)
            if decision is None:
                return None
            self._decision_cache.move_to_end(key)
            return decision

    def _cache_put(self, key: str, decision: ActionDecision) -> None:
        if self.cache_size <= 0:
            return
        with self._cache_lock:
            self._decision_cache[key] = decision
            self._decision_cache.move_to_end(key)
            while len(self._decision_cache) > self.cache_size:
                self._decision_cache.popitem(last=False)

    def _fast_path_decision(self, legal_actions: list[dict[str, Any]]) -> ActionDecision | None:
        if len(legal_actions) == 1:
            only = legal_actions[0]
            decision_amount = only.get("max_amount") or only.get("min_amount")
            if only["type"] in {"bet", "raise", "all_in"}:
                return ActionDecision(action_type=only["type"], amount=decision_amount)
            return ActionDecision(action_type=only["type"])

        legal_types = {item["type"] for item in legal_actions}
        if legal_types == {"check"}:
            return ActionDecision(action_type="check")
        return None

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActionDecision:
    action_type: str
    amount: int | None = None


class OpponentPolicy(Protocol):
    def decide_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> ActionDecision:
        ...


class DeterministicPolicy:
    """Safe fallback policy that always returns a legal action preference order."""

    def decide_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> ActionDecision:
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

    def __init__(
        self,
        api_key: str | None,
        model: str,
        timeout_ms: int,
        retries: int = 1,
        fallback: OpponentPolicy | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = max(1.0, timeout_ms / 1000.0)
        self.retries = max(0, retries)
        self.fallback = fallback or DeterministicPolicy()

    @classmethod
    def from_env(cls) -> "GeminiPolicy":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        timeout_ms = int(os.getenv("LLM_TIMEOUT_MS", "5000"))
        retries = int(os.getenv("LLM_RETRIES", "1"))
        return cls(api_key=api_key, model=model, timeout_ms=timeout_ms, retries=retries)

    def decide_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> ActionDecision:
        if not self.api_key:
            return self.fallback.decide_action(game_view, legal_actions)

        for attempt in range(self.retries + 1):
            try:
                response_text = self._request_action(game_view, legal_actions)
                parsed = self._parse_json_response(response_text)
                action_type = str(parsed.get("action_type", "")).strip().lower()
                amount = parsed.get("amount")
                if isinstance(amount, float):
                    amount = int(amount)
                if amount is not None and not isinstance(amount, int):
                    amount = None
                if action_type:
                    return ActionDecision(action_type=action_type, amount=amount)
            except Exception as exc:  # pragma: no cover - network errors vary by environment
                logger.warning("Gemini decision attempt %s failed: %s", attempt + 1, exc)

        return self.fallback.decide_action(game_view, legal_actions)

    def _request_action(self, game_view: dict[str, Any], legal_actions: list[dict[str, Any]]) -> str:
        if not self.api_key:
            raise RuntimeError("Gemini API key missing.")

        prompt = (
            "You are a heads-up no-limit Texas Hold'em bot. "
            "Return exactly one legal action as JSON only. "
            "Do not include markdown fences or explanations.\n\n"
            "Allowed schema:\n"
            "{\"action_type\": \"fold|check|call|bet|raise|all_in\", \"amount\": <integer optional>}\n\n"
            "Choose from legal_actions only. If action_type is bet/raise/all_in, include amount.\n\n"
            f"game_view={json.dumps(game_view, separators=(',', ':'))}\n"
            f"legal_actions={json.dumps(legal_actions, separators=(',', ':'))}"
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        model = urllib.parse.quote(self.model, safe="")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - depends on network/API state
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini API HTTP error {exc.code}: {body}") from exc

        parsed = json.loads(response_body)
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

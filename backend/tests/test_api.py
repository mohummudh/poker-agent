from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_create_session_and_fetch_state() -> None:
    create_resp = client.post("/api/sessions")
    assert create_resp.status_code == 200
    state = create_resp.json()

    session_id = state["sessionId"]
    fetch_resp = client.get(f"/api/sessions/{session_id}")
    assert fetch_resp.status_code == 200
    fetched = fetch_resp.json()
    assert fetched["sessionId"] == session_id
    assert fetched["pot"] == 3


def test_invalid_action_returns_422_with_legal_actions() -> None:
    create_resp = client.post("/api/sessions")
    session_id = create_resp.json()["sessionId"]

    invalid_resp = client.post(
        f"/api/sessions/{session_id}/actions",
        json={"actionType": "raise", "amount": 1},
    )
    assert invalid_resp.status_code == 422
    payload = invalid_resp.json()
    assert "legalActions" in payload["detail"]
    assert len(payload["detail"]["legalActions"]) > 0


def test_human_action_triggers_ai_action_and_replay_available() -> None:
    create_resp = client.post("/api/sessions")
    session_id = create_resp.json()["sessionId"]

    action_resp = client.post(
        f"/api/sessions/{session_id}/actions",
        json={"actionType": "call"},
    )
    assert action_resp.status_code == 200
    resolution = action_resp.json()
    actors = {event["actor"] for event in resolution["appliedEvents"]}
    assert "human" in actors
    assert "opponent" in actors

    hands_resp = client.get(f"/api/sessions/{session_id}/hands")
    assert hands_resp.status_code == 200
    hands = hands_resp.json()
    assert len(hands) >= 1

    hand_id = hands[0]["handId"]
    replay_resp = client.get(f"/api/sessions/{session_id}/hands/{hand_id}/replay")
    assert replay_resp.status_code == 200
    replay = replay_resp.json()
    assert replay["handId"] == hand_id
    assert len(replay["events"]) >= 1

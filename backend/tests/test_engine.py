from backend.app.engine import HeadsUpSession, InvalidActionError, build_shuffled_deck
from backend.app.opponent import DeterministicPolicy


def test_deck_is_deterministic_and_unique() -> None:
    deck_a = build_shuffled_deck("seed-123")
    deck_b = build_shuffled_deck("seed-123")
    assert deck_a == deck_b
    assert len(deck_a) == 52
    assert len(set(deck_a)) == 52


def test_initial_state_and_legal_actions() -> None:
    session = HeadsUpSession(session_id="s1", opponent_policy=DeterministicPolicy())
    state = session.get_state()

    assert state.street == "preflop"
    assert state.pot == 3
    assert state.players.human.is_button is True
    action_types = {action.type for action in state.legal_actions}
    assert {"fold", "call", "raise", "all_in"}.issubset(action_types)


def test_min_raise_validation() -> None:
    session = HeadsUpSession(session_id="s2", opponent_policy=DeterministicPolicy())

    try:
        session.process_human_action("raise", amount=2)
        assert False, "Expected invalid action"
    except InvalidActionError as exc:
        legal_types = {item.type for item in exc.legal_actions}
        assert "raise" in legal_types


def test_unmatched_chips_return_on_uneven_all_in_showdown() -> None:
    session = HeadsUpSession(
        session_id="s3",
        opponent_policy=DeterministicPolicy(),
        starting_stacks={"human": 200, "opponent": 40},
    )

    session.process_human_action("all_in", amount=199)
    state = session.get_state()

    assert state.status in {"hand_complete", "session_complete"}
    assert state.players.human.stack >= 160
    assert state.players.human.stack + state.players.opponent.stack == 240

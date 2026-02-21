from __future__ import annotations

import itertools
import random
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from .models import (
    ActionType,
    HandReplayModel,
    HandSummaryModel,
    LegalActionModel,
    ReplayEventModel,
    SessionPlayersModel,
    SessionStateModel,
)
from .opponent import ActionDecision, OpponentPolicy

PlayerId = Literal["human", "opponent"]
Winner = Literal["human", "opponent", "split"]

RANK_ORDER = "23456789TJQKA"
SUITS = "cdhs"


class InvalidActionError(ValueError):
    def __init__(self, message: str, legal_actions: list[LegalActionModel]) -> None:
        super().__init__(message)
        self.legal_actions = legal_actions


class SessionFlowError(ValueError):
    pass


@dataclass
class LegalActionInternal:
    type: ActionType
    min_amount: int | None = None
    max_amount: int | None = None
    to_call: int | None = None

    def to_model(self) -> LegalActionModel:
        return LegalActionModel(
            type=self.type,
            min_amount=self.min_amount,
            max_amount=self.max_amount,
            to_call=self.to_call,
        )


@dataclass
class PlayerInternal:
    id: PlayerId
    name: str
    stack: int
    is_button: bool
    hole_cards: list[str] = field(default_factory=list)
    cards_visible: bool = False
    folded: bool = False
    all_in: bool = False
    committed: int = 0
    contributed: int = 0


@dataclass
class HandInternal:
    hand_id: str
    seed: str
    street: Literal["preflop", "flop", "turn", "river", "showdown"]
    players: dict[PlayerId, PlayerInternal]
    deck: list[str]
    board: list[str]
    pot: int
    current_bet: int
    last_raise_size: int
    actor_to_act: PlayerId | None
    pending_actors: set[PlayerId]
    action_feed: list[ReplayEventModel]
    started_at: str
    status: Literal["in_progress", "hand_complete"]
    event_counter: int = 0
    final_winner: Winner | None = None
    archived: bool = False


class HandEvaluator:
    def __init__(self) -> None:
        self._treys_evaluator = None
        self._treys_card = None
        try:
            from treys import Card as TreysCard  # type: ignore
            from treys import Evaluator as TreysEvaluator  # type: ignore

            self._treys_card = TreysCard
            self._treys_evaluator = TreysEvaluator()
        except Exception:
            self._treys_evaluator = None
            self._treys_card = None

    def evaluate_winner(self, board: list[str], human_hole: list[str], opponent_hole: list[str]) -> Winner:
        if self._treys_evaluator and self._treys_card:
            card_factory = self._treys_card
            evaluator = self._treys_evaluator
            board_cards = [card_factory.new(card) for card in board]
            human_cards = [card_factory.new(card) for card in human_hole]
            opponent_cards = [card_factory.new(card) for card in opponent_hole]
            human_score = evaluator.evaluate(board_cards, human_cards)
            opponent_score = evaluator.evaluate(board_cards, opponent_cards)
            if human_score < opponent_score:
                return "human"
            if opponent_score < human_score:
                return "opponent"
            return "split"

        human_rank = self._best_rank(board + human_hole)
        opponent_rank = self._best_rank(board + opponent_hole)
        if human_rank > opponent_rank:
            return "human"
        if opponent_rank > human_rank:
            return "opponent"
        return "split"

    def _best_rank(self, cards: list[str]) -> tuple[int, tuple[int, ...]]:
        best: tuple[int, tuple[int, ...]] | None = None
        for combo in itertools.combinations(cards, 5):
            rank = self._rank_five(list(combo))
            if best is None or rank > best:
                best = rank
        if best is None:
            raise RuntimeError("Could not evaluate hand rank.")
        return best

    def _rank_five(self, cards: list[str]) -> tuple[int, tuple[int, ...]]:
        rank_values = sorted((RANK_ORDER.index(card[0]) + 2 for card in cards), reverse=True)
        suits = [card[1] for card in cards]
        counts = Counter(rank_values)

        is_flush = len(set(suits)) == 1
        straight_high = self._straight_high(rank_values)
        sorted_counts = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)

        if is_flush and straight_high is not None:
            return 8, (straight_high,)

        if sorted_counts[0][1] == 4:
            four_rank = sorted_counts[0][0]
            kicker = sorted_counts[1][0]
            return 7, (four_rank, kicker)

        if sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2:
            return 6, (sorted_counts[0][0], sorted_counts[1][0])

        if is_flush:
            return 5, tuple(rank_values)

        if straight_high is not None:
            return 4, (straight_high,)

        if sorted_counts[0][1] == 3:
            trips = sorted_counts[0][0]
            kickers = sorted((item[0] for item in sorted_counts[1:]), reverse=True)
            return 3, (trips, *kickers)

        if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
            pair_high = max(sorted_counts[0][0], sorted_counts[1][0])
            pair_low = min(sorted_counts[0][0], sorted_counts[1][0])
            kicker = sorted_counts[2][0]
            return 2, (pair_high, pair_low, kicker)

        if sorted_counts[0][1] == 2:
            pair = sorted_counts[0][0]
            kickers = sorted((item[0] for item in sorted_counts[1:]), reverse=True)
            return 1, (pair, *kickers)

        return 0, tuple(rank_values)

    def _straight_high(self, values: list[int]) -> int | None:
        unique = sorted(set(values), reverse=True)
        if len(unique) < 5:
            return None

        for idx in range(len(unique) - 4):
            window = unique[idx : idx + 5]
            if window[0] - window[-1] == 4 and len(window) == 5:
                return window[0]

        if {14, 5, 4, 3, 2}.issubset(set(unique)):
            return 5

        return None


def other_player(player_id: PlayerId) -> PlayerId:
    return "opponent" if player_id == "human" else "human"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_shuffled_deck(seed: str) -> list[str]:
    deck = [f"{rank}{suit}" for rank in RANK_ORDER for suit in SUITS]
    rng = random.Random(seed)
    rng.shuffle(deck)
    return deck


class HeadsUpSession:
    def __init__(
        self,
        session_id: str,
        opponent_policy: OpponentPolicy,
        small_blind: int = 1,
        big_blind: int = 2,
        starting_stacks: int | dict[PlayerId, int] = 200,
    ) -> None:
        self.session_id = session_id
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.opponent_policy = opponent_policy
        self.evaluator = HandEvaluator()

        if isinstance(starting_stacks, int):
            self.stacks: dict[PlayerId, int] = {"human": starting_stacks, "opponent": starting_stacks}
        else:
            self.stacks = {
                "human": int(starting_stacks["human"]),
                "opponent": int(starting_stacks["opponent"]),
            }

        self.button_player: PlayerId = "human"
        self.hand_counter = 0
        self.completed_replays: dict[str, HandReplayModel] = {}
        self.completed_summaries: list[HandSummaryModel] = []
        self.current_hand: HandInternal | None = None
        self._begin_new_hand()

    def get_state(self) -> SessionStateModel:
        hand = self._require_hand()
        if hand.status == "in_progress":
            status: Literal["in_progress", "hand_complete", "session_complete"] = "in_progress"
        elif min(self.stacks.values()) <= 0:
            status = "session_complete"
        else:
            status = "hand_complete"

        legal_actions = (
            [item.to_model() for item in self._legal_actions(hand, "human")]
            if hand.status == "in_progress" and hand.actor_to_act == "human"
            else []
        )

        human = hand.players["human"]
        opponent = hand.players["opponent"]
        human_model = self._player_state_model(human, reveal=True)
        opponent_model = self._player_state_model(opponent, reveal=opponent.cards_visible)

        return SessionStateModel(
            session_id=self.session_id,
            hand_id=hand.hand_id,
            street=hand.street,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            pot=hand.pot,
            board=list(hand.board),
            players=SessionPlayersModel(human=human_model, opponent=opponent_model),
            legal_actions=legal_actions,
            action_feed=list(hand.action_feed),
            status=status,
        )

    def list_hands(self) -> list[HandSummaryModel]:
        hand = self._require_hand()
        current_summary = HandSummaryModel(
            hand_id=hand.hand_id,
            started_at=hand.started_at,
            winner=hand.final_winner,
            final_pot=hand.pot,
        )
        return [current_summary, *self.completed_summaries]

    def get_replay(self, hand_id: str) -> HandReplayModel:
        hand = self._require_hand()
        if hand.hand_id == hand_id:
            return self._to_replay(hand)
        replay = self.completed_replays.get(hand_id)
        if not replay:
            raise KeyError(f"Hand replay not found: {hand_id}")
        return replay

    def process_human_action(self, action_type: ActionType, amount: int | None = None) -> list[ReplayEventModel]:
        hand = self._require_hand()
        if hand.status != "in_progress":
            raise SessionFlowError("Hand is complete. Start the next hand first.")
        if hand.actor_to_act != "human":
            raise SessionFlowError("It is not the human player's turn.")

        start_index = len(hand.action_feed)
        self._apply_action(hand, "human", action_type, amount)

        if hand.status == "in_progress" and hand.actor_to_act == "opponent":
            legal_for_opponent = self._legal_actions(hand, "opponent")
            legal_payload = [
                {
                    "type": item.type,
                    "min_amount": item.min_amount,
                    "max_amount": item.max_amount,
                    "to_call": item.to_call,
                }
                for item in legal_for_opponent
            ]
            decision = self.opponent_policy.decide_action(
                game_view=self._opponent_game_view(hand),
                legal_actions=legal_payload,
            )
            sanitized = self._sanitize_decision(decision, legal_for_opponent)
            self._apply_action(hand, "opponent", sanitized.action_type, sanitized.amount)

        return hand.action_feed[start_index:]

    def start_next_hand(self) -> SessionStateModel:
        hand = self._require_hand()
        if hand.status != "hand_complete":
            raise SessionFlowError("Current hand is still in progress.")
        if min(self.stacks.values()) <= 0:
            raise SessionFlowError("A player is busted. Use rebuy before starting a new hand.")

        self._archive_current_hand()
        self.button_player = other_player(self.button_player)
        self._begin_new_hand()
        return self.get_state()

    def rebuy_busted_and_start(self, stack_amount: int = 200) -> SessionStateModel:
        hand = self._require_hand()
        if hand.status == "in_progress":
            raise SessionFlowError("Cannot rebuy during an active hand.")

        for player_id in ("human", "opponent"):
            if self.stacks[player_id] <= 0:
                self.stacks[player_id] = stack_amount

        if min(self.stacks.values()) <= 0:
            raise SessionFlowError("Rebuy did not recover busted players.")

        self._archive_current_hand()
        self.button_player = other_player(self.button_player)
        self._begin_new_hand()
        return self.get_state()

    def _begin_new_hand(self) -> None:
        if min(self.stacks.values()) <= 0:
            raise SessionFlowError("Cannot start hand with busted players.")

        self.hand_counter += 1
        hand_id = f"hand-{self.hand_counter:03d}"
        seed = f"{self.session_id}:{self.hand_counter}"
        deck = build_shuffled_deck(seed)
        button = self.button_player
        blind_order = [button, other_player(button)]

        players: dict[PlayerId, PlayerInternal] = {
            "human": PlayerInternal(
                id="human",
                name="You",
                stack=self.stacks["human"],
                is_button=button == "human",
                cards_visible=True,
            ),
            "opponent": PlayerInternal(
                id="opponent",
                name="LLM Bot",
                stack=self.stacks["opponent"],
                is_button=button == "opponent",
                cards_visible=False,
            ),
        }

        for _ in range(2):
            for player_id in blind_order:
                players[player_id].hole_cards.append(deck.pop())

        hand = HandInternal(
            hand_id=hand_id,
            seed=seed,
            street="preflop",
            players=players,
            deck=deck,
            board=[],
            pot=0,
            current_bet=0,
            last_raise_size=self.big_blind,
            actor_to_act=None,
            pending_actors=set(),
            action_feed=[],
            started_at=now_iso(),
            status="in_progress",
        )

        self._add_event(hand, "system", f"Hand started. Blinds {self.small_blind}/{self.big_blind}.")

        small_blind_player = button
        big_blind_player = other_player(button)
        sb_paid = self._commit_chips(hand, small_blind_player, self.small_blind)
        bb_paid = self._commit_chips(hand, big_blind_player, self.big_blind)

        self._add_event(hand, small_blind_player, "post_small_blind", amount=sb_paid)
        self._add_event(hand, big_blind_player, "post_big_blind", amount=bb_paid)

        hand.current_bet = max(hand.players["human"].committed, hand.players["opponent"].committed)
        hand.last_raise_size = self.big_blind
        hand.pending_actors = self._active_not_all_in(hand)
        hand.actor_to_act = self._first_pending_actor(hand)

        self.current_hand = hand

        if self._all_active_all_in(hand):
            self._runout_and_resolve_showdown(hand)

    def _archive_current_hand(self) -> None:
        hand = self._require_hand()
        if hand.archived:
            return
        replay = self._to_replay(hand)
        self.completed_replays[hand.hand_id] = replay
        self.completed_summaries.insert(
            0,
            HandSummaryModel(
                hand_id=hand.hand_id,
                started_at=hand.started_at,
                winner=hand.final_winner,
                final_pot=hand.pot,
            ),
        )
        hand.archived = True

    def _apply_action(self, hand: HandInternal, actor: PlayerId, action_type: ActionType, amount: int | None) -> None:
        if hand.actor_to_act != actor:
            raise SessionFlowError("Action attempted out of turn.")

        legal_actions = self._legal_actions(hand, actor)
        legal_by_type = {item.type: item for item in legal_actions}
        if action_type not in legal_by_type:
            raise InvalidActionError("Illegal action for current game state.", [item.to_model() for item in legal_actions])

        player = hand.players[actor]
        to_call = max(0, hand.current_bet - player.committed)

        if action_type == "fold":
            player.folded = True
            hand.pending_actors.discard(actor)
            self._add_event(hand, actor, "fold")

        elif action_type == "check":
            hand.pending_actors.discard(actor)
            self._add_event(hand, actor, "check")

        elif action_type == "call":
            paid = self._commit_chips(hand, actor, min(to_call, player.stack))
            hand.pending_actors.discard(actor)
            self._add_event(hand, actor, "call", amount=paid)

        elif action_type in {"bet", "raise"}:
            legal = legal_by_type[action_type]
            if amount is None:
                raise InvalidActionError("Amount is required for bet/raise actions.", [item.to_model() for item in legal_actions])
            if legal.min_amount is None or legal.max_amount is None:
                raise InvalidActionError("Action does not support amount in this state.", [item.to_model() for item in legal_actions])

            if amount < legal.min_amount or amount > legal.max_amount:
                raise InvalidActionError("Bet size is out of legal range.", [item.to_model() for item in legal_actions])

            previous_bet = hand.current_bet
            paid = self._commit_chips(hand, actor, amount)
            new_bet = player.committed
            raise_size = new_bet - previous_bet
            hand.current_bet = new_bet
            hand.last_raise_size = raise_size
            hand.pending_actors = self._active_not_all_in(hand) - {actor}
            self._add_event(hand, actor, action_type, amount=paid)

        elif action_type == "all_in":
            if player.stack <= 0:
                raise InvalidActionError("Player cannot go all-in with zero stack.", [item.to_model() for item in legal_actions])
            previous_bet = hand.current_bet
            paid = self._commit_chips(hand, actor, player.stack)
            new_bet = player.committed
            if new_bet > previous_bet:
                raise_size = new_bet - previous_bet
                hand.current_bet = new_bet
                if raise_size >= hand.last_raise_size:
                    hand.last_raise_size = raise_size
                hand.pending_actors = self._active_not_all_in(hand) - {actor}
            else:
                hand.pending_actors.discard(actor)
            self._add_event(hand, actor, "all_in", amount=paid)

        else:
            raise InvalidActionError("Unsupported action type.", [item.to_model() for item in legal_actions])

        self._progress_game(hand)

    def _progress_game(self, hand: HandInternal) -> None:
        active_players = [player for player in hand.players.values() if not player.folded]
        if len(active_players) == 1:
            self._resolve_fold_win(hand, active_players[0].id)
            return

        if self._all_active_all_in(hand):
            self._runout_and_resolve_showdown(hand)
            return

        if not hand.pending_actors:
            self._advance_street_or_resolve(hand)
            return

        hand.actor_to_act = self._first_pending_actor(hand)

    def _resolve_fold_win(self, hand: HandInternal, winner: PlayerId) -> None:
        hand.players[winner].stack += hand.pot
        hand.players["human"].cards_visible = True
        hand.players["opponent"].cards_visible = True
        hand.status = "hand_complete"
        hand.final_winner = winner
        hand.actor_to_act = None
        hand.pending_actors.clear()
        hand.current_bet = 0

        self._sync_stacks(hand)
        self._add_event(hand, "system", f"{winner} wins after fold.")

    def _advance_street_or_resolve(self, hand: HandInternal) -> None:
        if hand.street == "river":
            self._resolve_showdown(hand)
            return

        self._deal_next_street(hand)

        for player in hand.players.values():
            player.committed = 0

        hand.current_bet = 0
        hand.last_raise_size = self.big_blind

        if self._count_active_not_all_in(hand) <= 1:
            self._runout_and_resolve_showdown(hand)
            return

        hand.pending_actors = self._active_not_all_in(hand)
        hand.actor_to_act = self._first_pending_actor(hand)

    def _deal_next_street(self, hand: HandInternal) -> None:
        if hand.street == "preflop":
            hand.street = "flop"
            hand.board.extend([hand.deck.pop(), hand.deck.pop(), hand.deck.pop()])
            self._add_event(hand, "system", "flop_dealt")
            return

        if hand.street == "flop":
            hand.street = "turn"
            hand.board.append(hand.deck.pop())
            self._add_event(hand, "system", "turn_dealt")
            return

        if hand.street == "turn":
            hand.street = "river"
            hand.board.append(hand.deck.pop())
            self._add_event(hand, "system", "river_dealt")
            return

        raise SessionFlowError("Cannot deal next street from current state.")

    def _runout_and_resolve_showdown(self, hand: HandInternal) -> None:
        while len(hand.board) < 5:
            if len(hand.board) == 0:
                hand.street = "flop"
                hand.board.extend([hand.deck.pop(), hand.deck.pop(), hand.deck.pop()])
                self._add_event(hand, "system", "flop_dealt")
            elif len(hand.board) == 3:
                hand.street = "turn"
                hand.board.append(hand.deck.pop())
                self._add_event(hand, "system", "turn_dealt")
            elif len(hand.board) == 4:
                hand.street = "river"
                hand.board.append(hand.deck.pop())
                self._add_event(hand, "system", "river_dealt")

        self._resolve_showdown(hand)

    def _resolve_showdown(self, hand: HandInternal) -> None:
        hand.street = "showdown"

        human = hand.players["human"]
        opponent = hand.players["opponent"]

        winner = self.evaluator.evaluate_winner(hand.board, human.hole_cards, opponent.hole_cards)

        matched = min(human.contributed, opponent.contributed)
        unmatched_human = human.contributed - matched
        unmatched_opponent = opponent.contributed - matched

        if unmatched_human > 0:
            human.stack += unmatched_human
        if unmatched_opponent > 0:
            opponent.stack += unmatched_opponent

        contested = matched * 2
        if winner == "human":
            human.stack += contested
        elif winner == "opponent":
            opponent.stack += contested
        else:
            split_a = contested // 2
            split_b = contested - split_a
            if self.button_player == "human":
                human.stack += split_a
                opponent.stack += split_b
            else:
                opponent.stack += split_a
                human.stack += split_b

        hand.players["human"].cards_visible = True
        hand.players["opponent"].cards_visible = True
        hand.status = "hand_complete"
        hand.final_winner = winner
        hand.actor_to_act = None
        hand.pending_actors.clear()
        hand.current_bet = 0

        self._sync_stacks(hand)
        self._add_event(hand, "system", f"showdown_{winner}")

    def _sync_stacks(self, hand: HandInternal) -> None:
        self.stacks = {
            "human": hand.players["human"].stack,
            "opponent": hand.players["opponent"].stack,
        }

    def _legal_actions(self, hand: HandInternal, actor: PlayerId) -> list[LegalActionInternal]:
        player = hand.players[actor]
        if hand.status != "in_progress" or player.folded or player.all_in:
            return []

        to_call = max(0, hand.current_bet - player.committed)
        actions: list[LegalActionInternal] = []

        if to_call > 0:
            actions.append(LegalActionInternal(type="fold"))
            actions.append(LegalActionInternal(type="call", to_call=to_call))
        else:
            actions.append(LegalActionInternal(type="check"))

        if player.stack > 0:
            if hand.current_bet == 0:
                if player.stack >= self.big_blind:
                    actions.append(
                        LegalActionInternal(type="bet", min_amount=self.big_blind, max_amount=player.stack)
                    )
                actions.append(
                    LegalActionInternal(type="all_in", min_amount=player.stack, max_amount=player.stack)
                )
            else:
                min_raise = to_call + hand.last_raise_size
                if player.stack >= min_raise:
                    actions.append(
                        LegalActionInternal(type="raise", min_amount=min_raise, max_amount=player.stack)
                    )
                actions.append(
                    LegalActionInternal(type="all_in", min_amount=player.stack, max_amount=player.stack)
                )

        return actions

    def _sanitize_decision(
        self, decision: ActionDecision, legal_actions: list[LegalActionInternal]
    ) -> ActionDecision:
        legal_by_type = {item.type: item for item in legal_actions}
        if decision.action_type not in legal_by_type:
            return self._fallback_decision(legal_actions)

        legal = legal_by_type[decision.action_type]
        if decision.action_type in {"bet", "raise", "all_in"}:
            low = legal.min_amount
            high = legal.max_amount
            if low is None or high is None:
                return self._fallback_decision(legal_actions)
            amount = decision.amount if decision.amount is not None else low
            amount = max(low, min(high, int(amount)))
            return ActionDecision(action_type=decision.action_type, amount=amount)

        return ActionDecision(action_type=decision.action_type)

    def _fallback_decision(self, legal_actions: list[LegalActionInternal]) -> ActionDecision:
        by_type = {item.type: item for item in legal_actions}
        if "check" in by_type:
            return ActionDecision("check")
        if "call" in by_type:
            return ActionDecision("call")
        if "fold" in by_type:
            return ActionDecision("fold")
        if "bet" in by_type:
            return ActionDecision("bet", by_type["bet"].min_amount)
        if "raise" in by_type:
            return ActionDecision("raise", by_type["raise"].min_amount)
        if "all_in" in by_type:
            return ActionDecision("all_in", by_type["all_in"].max_amount)
        raise RuntimeError("No legal actions available.")

    def _opponent_game_view(self, hand: HandInternal) -> dict[str, Any]:
        human = hand.players["human"]
        opponent = hand.players["opponent"]
        return {
            "hand_id": hand.hand_id,
            "street": hand.street,
            "pot": hand.pot,
            "board": list(hand.board),
            "opponent_hole_cards": list(opponent.hole_cards),
            "stacks": {"human": human.stack, "opponent": opponent.stack},
            "committed": {"human": human.committed, "opponent": opponent.committed},
            "button": self.button_player,
            "blinds": {"small": self.small_blind, "big": self.big_blind},
        }

    def _commit_chips(self, hand: HandInternal, actor: PlayerId, amount: int) -> int:
        player = hand.players[actor]
        if amount <= 0 or player.stack <= 0:
            return 0
        paid = min(amount, player.stack)
        player.stack -= paid
        player.committed += paid
        player.contributed += paid
        hand.pot += paid
        if player.stack == 0:
            player.all_in = True
        return paid

    def _first_pending_actor(self, hand: HandInternal) -> PlayerId | None:
        order = self._action_order(hand)
        for player_id in order:
            if player_id in hand.pending_actors:
                return player_id
        return None

    def _action_order(self, hand: HandInternal) -> list[PlayerId]:
        if hand.street == "preflop":
            return [self.button_player, other_player(self.button_player)]
        return [other_player(self.button_player), self.button_player]

    def _active_not_all_in(self, hand: HandInternal) -> set[PlayerId]:
        return {
            player_id
            for player_id, player in hand.players.items()
            if not player.folded and not player.all_in
        }

    def _count_active_not_all_in(self, hand: HandInternal) -> int:
        return len(self._active_not_all_in(hand))

    def _all_active_all_in(self, hand: HandInternal) -> bool:
        active = [player for player in hand.players.values() if not player.folded]
        return len(active) > 1 and all(player.all_in for player in active)

    def _player_state_model(self, player: PlayerInternal, reveal: bool) -> Any:
        hole_cards = list(player.hole_cards if reveal else ["??", "??"])
        from .models import PlayerStateModel

        return PlayerStateModel(
            id=player.id,
            name=player.name,
            stack=player.stack,
            is_button=player.is_button,
            hole_cards=hole_cards,
            cards_visible=reveal,
        )

    def _to_replay(self, hand: HandInternal) -> HandReplayModel:
        return HandReplayModel(
            hand_id=hand.hand_id,
            seed=hand.seed,
            blinds={"smallBlind": self.small_blind, "bigBlind": self.big_blind},
            events=list(hand.action_feed),
        )

    def _add_event(
        self,
        hand: HandInternal,
        actor: Literal["human", "opponent", "system"],
        action: str,
        amount: int | None = None,
    ) -> None:
        hand.event_counter += 1
        event = ReplayEventModel(
            id=f"evt-{hand.event_counter:03d}",
            timestamp=now_iso(),
            street=hand.street,
            actor=actor,
            action=action,
            amount=amount,
            pot=hand.pot,
            board=list(hand.board),
            stacks={
                "human": hand.players["human"].stack,
                "opponent": hand.players["opponent"].stack,
            },
            hole_card_visibility={
                "human": True,
                "opponent": hand.players["opponent"].cards_visible,
            },
            seed_ref=hand.seed,
        )
        hand.action_feed.append(event)

    def _require_hand(self) -> HandInternal:
        if not self.current_hand:
            raise SessionFlowError("No active hand available.")
        return self.current_hand

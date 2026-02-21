from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


Street = Literal["preflop", "flop", "turn", "river", "showdown"]
ActionType = Literal["fold", "check", "call", "bet", "raise", "all_in"]
Actor = Literal["human", "opponent", "system"]
Winner = Literal["human", "opponent", "split"]



def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class PlayerStateModel(CamelModel):
    id: Literal["human", "opponent"]
    name: str
    stack: int
    is_button: bool
    hole_cards: List[str]
    cards_visible: bool


class LegalActionModel(CamelModel):
    type: ActionType
    min_amount: Optional[int] = None
    max_amount: Optional[int] = None
    to_call: Optional[int] = None


class ReplayEventModel(CamelModel):
    id: str
    timestamp: str
    street: Street
    actor: Actor
    action: str
    amount: Optional[int] = None
    pot: int
    board: List[str]
    stacks: Dict[Literal["human", "opponent"], int]
    hole_card_visibility: Dict[Literal["human", "opponent"], bool]
    seed_ref: str


class HandSummaryModel(CamelModel):
    hand_id: str
    started_at: str
    winner: Optional[Winner]
    final_pot: int


class HandReplayModel(CamelModel):
    hand_id: str
    seed: str
    blinds: Dict[Literal["smallBlind", "bigBlind"], int]
    events: List[ReplayEventModel]


class SessionPlayersModel(CamelModel):
    human: PlayerStateModel
    opponent: PlayerStateModel


class SessionStateModel(CamelModel):
    session_id: str
    hand_id: str
    street: Street
    small_blind: int
    big_blind: int
    pot: int
    board: List[str]
    players: SessionPlayersModel
    legal_actions: List[LegalActionModel]
    action_feed: List[ReplayEventModel]
    status: Literal["in_progress", "hand_complete", "session_complete"]


class HumanActionRequestModel(CamelModel):
    action_type: ActionType
    amount: Optional[int] = None


class ActionResolutionModel(CamelModel):
    session_state: SessionStateModel
    applied_events: List[ReplayEventModel]
    hand_complete: bool

export type Street = "preflop" | "flop" | "turn" | "river" | "showdown";
export type ActionType = "fold" | "check" | "call" | "bet" | "raise" | "all_in";

export interface PlayerState {
  id: "human" | "opponent";
  name: string;
  stack: number;
  isButton: boolean;
  holeCards: string[];
  cardsVisible: boolean;
}

export interface LegalAction {
  type: ActionType;
  minAmount?: number;
  maxAmount?: number;
  toCall?: number;
}

export interface ReplayEvent {
  id: string;
  timestamp: string;
  street: Street;
  actor: "human" | "opponent" | "system";
  action: string;
  amount?: number;
  pot: number;
  board: string[];
  stacks: Record<"human" | "opponent", number>;
  holeCardVisibility: Record<"human" | "opponent", boolean>;
}

export interface HandSummary {
  handId: string;
  startedAt: string;
  winner: "human" | "opponent" | "split" | null;
  finalPot: number;
}

export interface HandReplay {
  handId: string;
  seed: string;
  blinds: {
    smallBlind: number;
    bigBlind: number;
  };
  events: ReplayEvent[];
}

export interface SessionState {
  sessionId: string;
  handId: string;
  street: Street;
  smallBlind: number;
  bigBlind: number;
  pot: number;
  board: string[];
  players: {
    human: PlayerState;
    opponent: PlayerState;
  };
  legalActions: LegalAction[];
  actionFeed: ReplayEvent[];
  status: "in_progress" | "hand_complete" | "session_complete";
}

export interface HumanActionRequest {
  actionType: ActionType;
  amount?: number;
}

export interface ActionResolution {
  sessionState: SessionState;
  appliedEvents: ReplayEvent[];
  handComplete: boolean;
}

export type ThemeVariant = "pixel-retro";

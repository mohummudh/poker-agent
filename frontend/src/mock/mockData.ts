import type { ActionType, HandReplay, HandSummary, ReplayEvent, SessionState } from "../types/game";

function nowIsoPlus(seconds: number): string {
  return new Date(Date.now() + seconds * 1000).toISOString();
}

export function buildInitialMockState(): SessionState {
  const feed: ReplayEvent[] = [
    {
      id: "evt-001",
      timestamp: nowIsoPlus(-45),
      street: "preflop",
      actor: "system",
      action: "Hand started. Blinds posted 1/2.",
      pot: 3,
      board: [],
      stacks: { human: 199, opponent: 198 },
      holeCardVisibility: { human: true, opponent: false }
    },
    {
      id: "evt-002",
      timestamp: nowIsoPlus(-42),
      street: "preflop",
      actor: "human",
      action: "raise",
      amount: 6,
      pot: 9,
      board: [],
      stacks: { human: 193, opponent: 198 },
      holeCardVisibility: { human: true, opponent: false }
    },
    {
      id: "evt-003",
      timestamp: nowIsoPlus(-40),
      street: "preflop",
      actor: "opponent",
      action: "call",
      amount: 4,
      pot: 13,
      board: [],
      stacks: { human: 193, opponent: 194 },
      holeCardVisibility: { human: true, opponent: false }
    },
    {
      id: "evt-004",
      timestamp: nowIsoPlus(-36),
      street: "flop",
      actor: "system",
      action: "Flop dealt.",
      pot: 13,
      board: ["Qs", "7d", "2c"],
      stacks: { human: 193, opponent: 194 },
      holeCardVisibility: { human: true, opponent: false }
    }
  ];

  return {
    sessionId: "mock-session-001",
    handId: "hand-001",
    street: "flop",
    smallBlind: 1,
    bigBlind: 2,
    pot: 13,
    board: ["Qs", "7d", "2c"],
    players: {
      human: {
        id: "human",
        name: "You",
        stack: 193,
        isButton: true,
        holeCards: ["Ah", "Jh"],
        cardsVisible: true
      },
      opponent: {
        id: "opponent",
        name: "LLM Bot",
        stack: 194,
        isButton: false,
        holeCards: ["Kd", "9c"],
        cardsVisible: false
      }
    },
    legalActions: [
      { type: "fold" },
      { type: "check" },
      { type: "bet", minAmount: 2, maxAmount: 193 },
      { type: "all_in", minAmount: 193, maxAmount: 193 }
    ],
    actionFeed: feed,
    status: "in_progress"
  };
}

export function buildMockHandSummaries(currentHandId: string): HandSummary[] {
  return [
    {
      handId: currentHandId,
      startedAt: nowIsoPlus(-45),
      winner: null,
      finalPot: 13
    },
    {
      handId: "hand-000",
      startedAt: nowIsoPlus(-480),
      winner: "opponent",
      finalPot: 36
    }
  ];
}

export function buildMockReplays(currentState: SessionState): HandReplay[] {
  return [
    {
      handId: currentState.handId,
      seed: "mock-seed-current",
      blinds: { smallBlind: currentState.smallBlind, bigBlind: currentState.bigBlind },
      events: currentState.actionFeed
    },
    {
      handId: "hand-000",
      seed: "mock-seed-previous",
      blinds: { smallBlind: 1, bigBlind: 2 },
      events: [
        {
          id: "h0-001",
          timestamp: nowIsoPlus(-490),
          street: "preflop",
          actor: "human",
          action: "raise",
          amount: 8,
          pot: 11,
          board: [],
          stacks: { human: 192, opponent: 198 },
          holeCardVisibility: { human: true, opponent: false }
        },
        {
          id: "h0-002",
          timestamp: nowIsoPlus(-487),
          street: "preflop",
          actor: "opponent",
          action: "call",
          amount: 6,
          pot: 17,
          board: [],
          stacks: { human: 192, opponent: 192 },
          holeCardVisibility: { human: true, opponent: false }
        },
        {
          id: "h0-003",
          timestamp: nowIsoPlus(-485),
          street: "flop",
          actor: "system",
          action: "Flop dealt.",
          pot: 17,
          board: ["Tc", "7h", "4h"],
          stacks: { human: 192, opponent: 192 },
          holeCardVisibility: { human: true, opponent: false }
        },
        {
          id: "h0-004",
          timestamp: nowIsoPlus(-480),
          street: "showdown",
          actor: "system",
          action: "Opponent wins at showdown.",
          pot: 36,
          board: ["Tc", "7h", "4h", "2s", "Qd"],
          stacks: { human: 182, opponent: 218 },
          holeCardVisibility: { human: true, opponent: true }
        }
      ]
    }
  ];
}

function actionCost(actionType: ActionType, amount?: number): number {
  if (actionType === "fold" || actionType === "check") {
    return 0;
  }
  return Math.max(0, Math.floor(amount ?? 0));
}

function pickMockOpponentAction(state: SessionState): { type: ActionType; amount?: number } {
  if (state.status !== "in_progress") {
    return { type: "check" };
  }

  if (state.pot <= 20) {
    return { type: "check" };
  }

  if (state.pot <= 40) {
    return { type: "call", amount: 4 };
  }

  return { type: "all_in", amount: Math.min(36, state.players.opponent.stack) };
}

export function applyMockAction(state: SessionState, actionType: ActionType, amount?: number): SessionState {
  const next: SessionState = JSON.parse(JSON.stringify(state)) as SessionState;

  if (next.status !== "in_progress") {
    return next;
  }

  const humanCost = Math.min(actionCost(actionType, amount), next.players.human.stack);
  next.players.human.stack -= humanCost;
  next.pot += humanCost;

  const humanEvent: ReplayEvent = {
    id: `evt-${next.actionFeed.length + 1}`,
    timestamp: new Date().toISOString(),
    street: next.street,
    actor: "human",
    action: actionType,
    amount: humanCost > 0 ? humanCost : undefined,
    pot: next.pot,
    board: [...next.board],
    stacks: { human: next.players.human.stack, opponent: next.players.opponent.stack },
    holeCardVisibility: {
      human: true,
      opponent: next.players.opponent.cardsVisible
    }
  };
  next.actionFeed.push(humanEvent);

  if (actionType === "fold") {
    next.status = "hand_complete";
    next.players.opponent.cardsVisible = true;
    next.legalActions = [];
    next.actionFeed.push({
      id: `evt-${next.actionFeed.length + 1}`,
      timestamp: new Date().toISOString(),
      street: next.street,
      actor: "system",
      action: "Opponent wins after fold.",
      pot: next.pot,
      board: [...next.board],
      stacks: { human: next.players.human.stack, opponent: next.players.opponent.stack },
      holeCardVisibility: { human: true, opponent: true }
    });
    return next;
  }

  const bot = pickMockOpponentAction(next);
  const botCost = Math.min(actionCost(bot.type, bot.amount), next.players.opponent.stack);
  next.players.opponent.stack -= botCost;
  next.pot += botCost;

  next.actionFeed.push({
    id: `evt-${next.actionFeed.length + 1}`,
    timestamp: new Date().toISOString(),
    street: next.street,
    actor: "opponent",
    action: bot.type,
    amount: botCost > 0 ? botCost : undefined,
    pot: next.pot,
    board: [...next.board],
    stacks: { human: next.players.human.stack, opponent: next.players.opponent.stack },
    holeCardVisibility: { human: true, opponent: false }
  });

  if (actionType === "all_in" || bot.type === "all_in") {
    next.status = "hand_complete";
    next.street = "showdown";
    next.board = ["Qs", "7d", "2c", "9s", "Ac"];
    next.players.opponent.cardsVisible = true;
    next.legalActions = [];
    next.actionFeed.push({
      id: `evt-${next.actionFeed.length + 1}`,
      timestamp: new Date().toISOString(),
      street: "showdown",
      actor: "system",
      action: "Showdown reached.",
      pot: next.pot,
      board: [...next.board],
      stacks: { human: next.players.human.stack, opponent: next.players.opponent.stack },
      holeCardVisibility: { human: true, opponent: true }
    });
  }

  return next;
}

export function createNextMockHand(state: SessionState): SessionState {
  const handNumber = Number.parseInt(state.handId.split("-")[1] ?? "1", 10) + 1;
  return {
    sessionId: state.sessionId,
    handId: `hand-${handNumber.toString().padStart(3, "0")}`,
    street: "preflop",
    smallBlind: state.smallBlind,
    bigBlind: state.bigBlind,
    pot: 3,
    board: [],
    players: {
      human: {
        ...state.players.human,
        stack: Math.max(80, state.players.human.stack),
        holeCards: ["9h", "9d"],
        isButton: !state.players.human.isButton,
        cardsVisible: true
      },
      opponent: {
        ...state.players.opponent,
        stack: Math.max(80, state.players.opponent.stack),
        holeCards: ["As", "Qc"],
        isButton: !state.players.opponent.isButton,
        cardsVisible: false
      }
    },
    legalActions: [
      { type: "fold" },
      { type: "call", toCall: 1 },
      { type: "raise", minAmount: 4, maxAmount: Math.max(80, state.players.human.stack) }
    ],
    actionFeed: [
      {
        id: "evt-001",
        timestamp: new Date().toISOString(),
        street: "preflop",
        actor: "system",
        action: "New hand started. Blinds posted 1/2.",
        pot: 3,
        board: [],
        stacks: {
          human: Math.max(80, state.players.human.stack) - (state.players.human.isButton ? 2 : 1),
          opponent: Math.max(80, state.players.opponent.stack) - (state.players.opponent.isButton ? 2 : 1)
        },
        holeCardVisibility: { human: true, opponent: false }
      }
    ],
    status: "in_progress"
  };
}

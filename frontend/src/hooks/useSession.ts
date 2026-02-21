import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, pokerApi } from "../api/client";
import { applyMockAction, buildInitialMockState, buildMockHandSummaries, buildMockReplays, createNextMockHand } from "../mock/mockData";
import type { ActionType, HandReplay, HandSummary, SessionState } from "../types/game";

type SessionMode = "api" | "mock";

interface SessionModel {
  mode: SessionMode;
  session: SessionState | null;
  handSummaries: HandSummary[];
  selectedReplay: HandReplay | null;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  submitAction: (type: ActionType, amount?: number) => Promise<void>;
  nextHand: () => Promise<void>;
  selectReplay: (handId: string) => Promise<void>;
}

export function useSession(): SessionModel {
  const [mode, setMode] = useState<SessionMode>("api");
  const [session, setSession] = useState<SessionState | null>(null);
  const [handSummaries, setHandSummaries] = useState<HandSummary[]>([]);
  const [replays, setReplays] = useState<HandReplay[]>([]);
  const [selectedReplay, setSelectedReplay] = useState<HandReplay | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bootstrapMock = useCallback(() => {
    const mockSession = buildInitialMockState();
    const mockHands = buildMockHandSummaries(mockSession.handId);
    const mockReplays = buildMockReplays(mockSession);
    setMode("mock");
    setSession(mockSession);
    setHandSummaries(mockHands);
    setReplays(mockReplays);
    setSelectedReplay(mockReplays[0] ?? null);
    setLoading(false);
    setError("Backend not reachable. Running in local mock mode.");
  }, []);

  const refreshHandsFromApi = useCallback(async (sessionId: string) => {
    const hands = await pokerApi.listHands(sessionId);
    setHandSummaries(hands);
    if (hands.length > 0) {
      const replay = await pokerApi.getHandReplay(sessionId, hands[0].handId);
      setSelectedReplay(replay);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const initial = await pokerApi.createSession();
        if (cancelled) {
          return;
        }
        setMode("api");
        setSession(initial);
        await refreshHandsFromApi(initial.sessionId);
        if (!cancelled) {
          setError(null);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          bootstrapMock();
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [bootstrapMock, refreshHandsFromApi]);

  const submitAction = useCallback(
    async (type: ActionType, amount?: number) => {
      if (!session) {
        return;
      }
      setSubmitting(true);
      try {
        if (mode === "api") {
          const result = await pokerApi.submitAction(session.sessionId, { actionType: type, amount });
          setSession(result.sessionState);
          if (result.handComplete) {
            await refreshHandsFromApi(session.sessionId);
          }
          setError(null);
        } else {
          const updated = applyMockAction(session, type, amount);
          setSession(updated);
          const updatedReplay: HandReplay = {
            handId: updated.handId,
            seed: "mock-live-seed",
            blinds: { smallBlind: updated.smallBlind, bigBlind: updated.bigBlind },
            events: updated.actionFeed
          };
          setReplays((prev) => {
            const withoutCurrent = prev.filter((item) => item.handId !== updated.handId);
            return [updatedReplay, ...withoutCurrent];
          });
          setSelectedReplay(updatedReplay);
          setHandSummaries((prev) => {
            const current = prev.find((item) => item.handId === updated.handId);
            const winner =
              updated.status === "hand_complete"
                ? updated.players.human.stack >= updated.players.opponent.stack
                  ? "human"
                  : "opponent"
                : null;
            const summary: HandSummary = {
              handId: updated.handId,
              startedAt: current?.startedAt ?? new Date().toISOString(),
              winner,
              finalPot: updated.pot
            };
            return [summary, ...prev.filter((item) => item.handId !== updated.handId)];
          });
        }
      } catch (err) {
        if (err instanceof ApiError) {
          setError(`Action rejected (${err.status}).`);
        } else {
          setError("Action failed.");
        }
      } finally {
        setSubmitting(false);
      }
    },
    [mode, refreshHandsFromApi, session]
  );

  const nextHand = useCallback(async () => {
    if (!session) {
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "api") {
        const next = await pokerApi.nextHand(session.sessionId);
        setSession(next);
        setError(null);
      } else {
        const next = createNextMockHand(session);
        setSession(next);
        const replay: HandReplay = {
          handId: next.handId,
          seed: "mock-next-seed",
          blinds: { smallBlind: next.smallBlind, bigBlind: next.bigBlind },
          events: next.actionFeed
        };
        setReplays((prev) => [replay, ...prev]);
        setSelectedReplay(replay);
        setHandSummaries((prev) => [
          {
            handId: next.handId,
            startedAt: new Date().toISOString(),
            winner: null,
            finalPot: next.pot
          },
          ...prev
        ]);
      }
    } catch {
      setError("Could not start next hand.");
    } finally {
      setSubmitting(false);
    }
  }, [mode, session]);

  const selectReplay = useCallback(
    async (handId: string) => {
      if (!session) {
        return;
      }
      try {
        if (mode === "api") {
          const replay = await pokerApi.getHandReplay(session.sessionId, handId);
          setSelectedReplay(replay);
        } else {
          const replay = replays.find((item) => item.handId === handId) ?? null;
          setSelectedReplay(replay);
        }
      } catch {
        setError("Could not load replay.");
      }
    },
    [mode, replays, session]
  );

  return useMemo(
    () => ({
      mode,
      session,
      handSummaries,
      selectedReplay,
      loading,
      submitting,
      error,
      submitAction,
      nextHand,
      selectReplay
    }),
    [error, handSummaries, loading, mode, nextHand, selectReplay, selectedReplay, session, submitAction, submitting]
  );
}

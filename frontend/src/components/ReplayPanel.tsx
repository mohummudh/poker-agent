import { useEffect, useMemo, useState } from "react";
import type { HandReplay, HandSummary } from "../types/game";

interface ReplayPanelProps {
  handSummaries: HandSummary[];
  replay: HandReplay | null;
  onSelectHand: (handId: string) => Promise<void>;
}

function winnerLabel(winner: HandSummary["winner"]): string {
  if (winner === "human") {
    return "You";
  }
  if (winner === "opponent") {
    return "Bot";
  }
  if (winner === "split") {
    return "Split";
  }
  return "Live";
}

export function ReplayPanel({ handSummaries, replay, onSelectHand }: ReplayPanelProps) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    setStep(0);
  }, [replay?.handId]);

  const eventCount = replay?.events.length ?? 0;
  const currentEvent = useMemo(() => replay?.events[step] ?? null, [replay?.events, step]);

  return (
    <section className="pixel-panel replay-panel">
      <header className="panel-header">
        <h3 className="pixel-title-sm">Replay</h3>
      </header>

      <div className="hand-list" role="list">
        {handSummaries.map((hand) => (
          <button
            type="button"
            className={`pixel-btn hand-item ${replay?.handId === hand.handId ? "is-active" : ""}`}
            key={hand.handId}
            onClick={() => void onSelectHand(hand.handId)}
          >
            <span>{hand.handId}</span>
            <span>{winnerLabel(hand.winner)}</span>
          </button>
        ))}
      </div>

      <div className="replay-controls">
        <button
          type="button"
          className="pixel-btn dpad-btn"
          disabled={!replay || step <= 0}
          onClick={() => setStep((value) => Math.max(0, value - 1))}
        >
          <span>Left</span>
        </button>
        <button
          type="button"
          className="pixel-btn dpad-btn"
          disabled={!replay || step >= Math.max(0, eventCount - 1)}
          onClick={() => setStep((value) => Math.min(Math.max(0, eventCount - 1), value + 1))}
        >
          <span>Right</span>
        </button>
      </div>

      <div className="replay-event-view pixel-input">
        {currentEvent ? (
          <>
            <div>Step {step + 1}</div>
            <div>{currentEvent.street.toUpperCase()}</div>
            <div>
              {currentEvent.actor}: {currentEvent.action}
              {currentEvent.amount ? ` ${currentEvent.amount}` : ""}
            </div>
            <div>Pot {currentEvent.pot}</div>
          </>
        ) : (
          <span>No replay loaded.</span>
        )}
      </div>
    </section>
  );
}

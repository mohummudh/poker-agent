import { memo, useEffect, useMemo, useState } from "react";
import type { ActionType, LegalAction } from "../types/game";

interface ActionControlsProps {
  legalActions: LegalAction[];
  disabled: boolean;
  onSubmit: (type: ActionType, amount?: number) => Promise<void>;
}

const ACTION_ORDER: ActionType[] = ["fold", "check", "call", "bet", "raise", "all_in"];

function toLabel(action: ActionType): string {
  if (action === "all_in") {
    return "All-in";
  }
  return action.charAt(0).toUpperCase() + action.slice(1);
}

export const ActionControls = memo(function ActionControls({ legalActions, disabled, onSubmit }: ActionControlsProps) {
  const legalByType = useMemo(() => new Map(legalActions.map((item) => [item.type, item])), [legalActions]);
  const betLike = legalByType.get("raise") ?? legalByType.get("bet") ?? legalByType.get("all_in");

  const [amount, setAmount] = useState<number>(() => betLike?.minAmount ?? 0);

  useEffect(() => {
    setAmount(betLike?.minAmount ?? 0);
  }, [betLike?.maxAmount, betLike?.minAmount]);

  const min = betLike?.minAmount ?? 0;
  const max = betLike?.maxAmount ?? min;
  const canSize = Boolean(betLike);

  const clamp = (value: number): number => {
    if (!canSize) {
      return 0;
    }
    return Math.max(min, Math.min(max, Math.floor(value)));
  };

  const onAction = async (type: ActionType) => {
    if (disabled || !legalByType.has(type)) {
      return;
    }
    const shouldSendAmount = type === "bet" || type === "raise" || type === "all_in";
    await onSubmit(type, shouldSendAmount ? clamp(amount) : undefined);
  };

  return (
    <section className="pixel-panel action-controls stagger-pop">
      <header className="action-controls-header">
        <h3 className="pixel-title-sm">Your Move</h3>
        {canSize ? (
          <div className="bet-range">
            <span>Min {min}</span>
            <span>Max {max}</span>
          </div>
        ) : (
          <span className="bet-range">No sizing action available</span>
        )}
      </header>

      <div className="bet-size-row">
        <input
          className="pixel-slider"
          type="range"
          min={min}
          max={max}
          value={canSize ? amount : 0}
          step={1}
          disabled={!canSize || disabled}
          onChange={(event) => setAmount(clamp(Number(event.target.value)))}
          aria-label="Bet amount"
        />
        <input
          className="pixel-input bet-amount-input"
          type="number"
          min={min}
          max={max}
          value={canSize ? amount : 0}
          disabled={!canSize || disabled}
          onChange={(event) => setAmount(clamp(Number(event.target.value)))}
          aria-label="Bet amount input"
        />
      </div>

      <div className="action-grid">
        {ACTION_ORDER.map((type) => {
          const legal = legalByType.get(type);
          const isDisabled = disabled || !legal;
          const callSuffix = type === "call" && legal?.toCall ? ` ${legal.toCall}` : "";
          const sizeSuffix =
            (type === "bet" || type === "raise") && legal?.minAmount && legal?.maxAmount
              ? ` ${legal.minAmount}-${legal.maxAmount}`
              : "";
          const label = `${toLabel(type)}${callSuffix}${sizeSuffix}`;
          return (
            <button
              type="button"
              key={type}
              className="pixel-btn action-btn"
              disabled={isDisabled}
              onClick={() => void onAction(type)}
            >
              {label}
            </button>
          );
        })}
      </div>
    </section>
  );
});

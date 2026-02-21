import { memo } from "react";
import coinIcon from "../assets/pixel/coin.svg";
import type { Street } from "../types/game";
import { PixelCard } from "./PixelCard";

interface BoardStageProps {
  pot: number;
  street: Street;
  board: string[];
}

const BOARD_SLOTS = [0, 1, 2, 3, 4] as const;

export const BoardStage = memo(function BoardStage({ pot, street, board }: BoardStageProps) {
  return (
    <section className="board-stage stagger-pop">
      <div className="pot-badge pixel-panel">
        <img src={coinIcon} alt="" className="pixel-icon" />
        <span>Pot {pot}</span>
      </div>

      <div className="street-chip">{street.toUpperCase()}</div>

      <div className="board-card-row">
        {BOARD_SLOTS.map((slot) => (
          <PixelCard key={slot} card={board[slot]} hidden={!board[slot]} />
        ))}
      </div>
    </section>
  );
});

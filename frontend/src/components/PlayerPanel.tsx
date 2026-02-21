import { memo } from "react";
import coinIcon from "../assets/pixel/coin.svg";
import chipIcon from "../assets/pixel/chip.svg";
import type { PlayerState } from "../types/game";
import { PixelCard } from "./PixelCard";

interface PlayerPanelProps {
  player: PlayerState;
  roleLabel: string;
  revealCards: boolean;
  speechBubbleText?: string;
}

export const PlayerPanel = memo(function PlayerPanel({
  player,
  roleLabel,
  revealCards,
  speechBubbleText
}: PlayerPanelProps) {
  return (
    <section className="pixel-panel player-panel stagger-pop" data-role={player.id}>
      <div className="player-header">
        <div className="player-meta">
          <div className="player-name-line">
            <span className="player-role">{roleLabel}</span>
            <div className="player-name-row">
              <h2 className="pixel-title-sm">{player.name}</h2>
              {speechBubbleText ? (
                <span className="player-speech-bubble" aria-live="polite">
                  {speechBubbleText}
                </span>
              ) : null}
            </div>
          </div>
          <div className="chip-stack">
            <img src={chipIcon} alt="" className="pixel-icon" />
            <span>{player.stack} chips</span>
          </div>
        </div>
        {player.isButton ? <span className="dealer-medallion">D</span> : null}
      </div>

      <div className="card-row">
        <PixelCard card={player.holeCards[0]} hidden={!revealCards} size="sm" />
        <PixelCard card={player.holeCards[1]} hidden={!revealCards} size="sm" />
      </div>

      <div className="player-footer">
        <img src={coinIcon} alt="" className="pixel-icon" />
        <span>{player.cardsVisible || revealCards ? "Cards shown" : "Cards hidden"}</span>
      </div>
    </section>
  );
});

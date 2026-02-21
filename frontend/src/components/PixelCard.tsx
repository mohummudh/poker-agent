import { memo } from "react";
import type { CSSProperties } from "react";
import clubIcon from "../assets/pixel/suits/club.svg";
import diamondIcon from "../assets/pixel/suits/diamond.svg";
import heartIcon from "../assets/pixel/suits/heart.svg";
import spadeIcon from "../assets/pixel/suits/spade.svg";

interface PixelCardProps {
  card?: string;
  hidden?: boolean;
  size?: "sm" | "md";
}

const SUIT_META: Record<
  string,
  {
    icon: string;
    colorClass: "" | "is-red";
  }
> = {
  h: { icon: heartIcon, colorClass: "is-red" },
  d: { icon: diamondIcon, colorClass: "is-red" },
  c: { icon: clubIcon, colorClass: "" },
  s: { icon: spadeIcon, colorClass: "" }
};

function splitCard(card = "??"): { rank: string; suit: string } {
  if (card.length < 2) {
    return { rank: "?", suit: "?" };
  }
  const rank = card.slice(0, -1).toUpperCase();
  const suit = card.slice(-1).toLowerCase();
  return { rank, suit };
}

export const PixelCard = memo(function PixelCard({ card, hidden = false, size = "md" }: PixelCardProps) {
  const { rank, suit } = splitCard(card);
  const suitMeta = SUIT_META[suit] ?? SUIT_META.s;
  const style = {
    "--card-scale": size === "sm" ? "0.85" : "1"
  } as CSSProperties;

  if (hidden) {
    return (
      <div className="pixel-card pixel-card-hidden" style={style} aria-label="Hidden card">
        <div className="pixel-card-back-grid" />
      </div>
    );
  }

  return (
    <div className="pixel-card" style={style} aria-label={`Card ${rank}${suit.toUpperCase()}`}>
      <div className={`pixel-card-corner pixel-card-corner-top ${suitMeta.colorClass}`}>
        <span className="pixel-card-rank">{rank}</span>
        <img src={suitMeta.icon} alt="" className="pixel-card-suit-icon" />
      </div>

      <div className="pixel-card-face">
        <img src={suitMeta.icon} alt="" className="pixel-card-face-icon" />
      </div>

      <div className={`pixel-card-corner pixel-card-corner-bottom ${suitMeta.colorClass}`}>
        <span className="pixel-card-rank">{rank}</span>
        <img src={suitMeta.icon} alt="" className="pixel-card-suit-icon" />
      </div>
    </div>
  );
});

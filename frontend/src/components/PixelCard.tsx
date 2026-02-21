import type { CSSProperties } from "react";

interface PixelCardProps {
  card?: string;
  hidden?: boolean;
  size?: "sm" | "md";
}

const RED_SUITS = new Set(["h", "d"]);

function splitCard(card = "??"): { rank: string; suit: string } {
  if (card.length < 2) {
    return { rank: "?", suit: "?" };
  }
  const rank = card.slice(0, -1).toUpperCase();
  const suit = card.slice(-1).toLowerCase();
  return { rank, suit };
}

function suitToGlyph(suit: string): string {
  if (suit === "h") {
    return "H";
  }
  if (suit === "d") {
    return "D";
  }
  if (suit === "c") {
    return "C";
  }
  if (suit === "s") {
    return "S";
  }
  return "?";
}

export function PixelCard({ card, hidden = false, size = "md" }: PixelCardProps) {
  const { rank, suit } = splitCard(card);
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
      <span className={`pixel-card-rank ${RED_SUITS.has(suit) ? "is-red" : ""}`}>{rank}</span>
      <span className={`pixel-card-suit ${RED_SUITS.has(suit) ? "is-red" : ""}`}>{suitToGlyph(suit)}</span>
    </div>
  );
}

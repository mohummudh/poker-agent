import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlayerPanel } from "../components/PlayerPanel";

describe("PlayerPanel", () => {
  const basePlayer = {
    id: "opponent" as const,
    name: "LLM Bot",
    stack: 194,
    isButton: false,
    holeCards: ["Ah", "Kd"],
    cardsVisible: false
  };

  it("keeps opponent cards hidden before reveal", () => {
    render(<PlayerPanel player={basePlayer} roleLabel="Opponent" revealCards={false} />);
    expect(screen.getAllByLabelText("Hidden card")).toHaveLength(2);
  });

  it("shows cards when reveal is enabled", () => {
    render(<PlayerPanel player={basePlayer} roleLabel="Opponent" revealCards />);
    expect(screen.getByLabelText("Card AH")).toBeInTheDocument();
    expect(screen.getByLabelText("Card KD")).toBeInTheDocument();
  });
});

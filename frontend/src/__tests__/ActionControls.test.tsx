import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ActionControls } from "../components/ActionControls";

describe("ActionControls", () => {
  it("clamps bet amount to legal max before submit", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ActionControls
        legalActions={[
          { type: "check" },
          { type: "bet", minAmount: 2, maxAmount: 5 },
          { type: "all_in", minAmount: 20, maxAmount: 20 }
        ]}
        disabled={false}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText("Bet amount input"), {
      target: { value: "99" }
    });

    fireEvent.click(screen.getByRole("button", { name: /^Bet /i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("bet", 5);
    });
  });

  it("disables illegal actions", () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ActionControls
        legalActions={[{ type: "check" }]}
        disabled={false}
        onSubmit={onSubmit}
      />
    );

    expect(screen.getByRole("button", { name: /^Fold$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^Check$/i })).toBeEnabled();
  });
});

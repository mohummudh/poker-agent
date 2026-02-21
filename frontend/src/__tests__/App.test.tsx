import { render, screen } from "@testing-library/react";
import App from "../App";

describe("App", () => {
  it("boots into mock mode when API is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    try {
      render(<App />);
      expect(await screen.findByText(/^Mock Mode$/i)).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: /pixel poker duel/i })).toBeInTheDocument();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

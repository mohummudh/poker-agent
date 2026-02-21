import type { ActionResolution, HandReplay, HandSummary, HumanActionRequest, SessionState } from "../types/game";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class PokerApiClient {
  constructor(private readonly baseUrl = "/api") {}

  async createSession(): Promise<SessionState> {
    return this.request<SessionState>("/sessions", { method: "POST" });
  }

  async getSession(sessionId: string): Promise<SessionState> {
    return this.request<SessionState>(`/sessions/${sessionId}`);
  }

  async submitAction(sessionId: string, payload: HumanActionRequest): Promise<ActionResolution> {
    return this.request<ActionResolution>(`/sessions/${sessionId}/actions`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async nextHand(sessionId: string): Promise<SessionState> {
    return this.request<SessionState>(`/sessions/${sessionId}/next-hand`, { method: "POST" });
  }

  async listHands(sessionId: string): Promise<HandSummary[]> {
    return this.request<HandSummary[]>(`/sessions/${sessionId}/hands`);
  }

  async getHandReplay(sessionId: string, handId: string): Promise<HandReplay> {
    return this.request<HandReplay>(`/sessions/${sessionId}/hands/${handId}/replay`);
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers
      }
    });

    if (!response.ok) {
      const message = `API request failed (${response.status})`;
      throw new ApiError(message, response.status);
    }

    return (await response.json()) as T;
  }
}

export const pokerApi = new PokerApiClient();

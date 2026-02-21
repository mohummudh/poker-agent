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

  async rebuy(sessionId: string): Promise<SessionState> {
    return this.request<SessionState>(`/sessions/${sessionId}/rebuy`, { method: "POST" });
  }

  async listHands(sessionId: string): Promise<HandSummary[]> {
    return this.request<HandSummary[]>(`/sessions/${sessionId}/hands`);
  }

  async getHandReplay(sessionId: string, handId: string): Promise<HandReplay> {
    return this.request<HandReplay>(`/sessions/${sessionId}/hands/${handId}/replay`);
  }

  async openSessionSocket(sessionId: string): Promise<PokerSessionSocket> {
    const httpUrl = new URL(`${this.baseUrl}/ws/sessions/${sessionId}`, window.location.origin);
    const wsUrl = httpUrl.toString().replace(/^http/i, "ws");
    const socket = new PokerSessionSocket(wsUrl);
    await socket.ready();
    return socket;
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

interface PendingRequest<T> {
  resolve: (value: T) => void;
  reject: (error: Error) => void;
  timeoutId: number;
}

type SocketMessage = {
  type: string;
  requestId?: string;
  payload?: unknown;
  status?: number;
  message?: string;
};

export class PokerSessionSocket {
  private socket: WebSocket;
  private readonly pending = new Map<string, PendingRequest<unknown>>();
  private readonly readyPromise: Promise<void>;
  private requestCounter = 0;

  constructor(url: string) {
    this.socket = new WebSocket(url);
    this.readyPromise = new Promise<void>((resolve, reject) => {
      const onOpen = () => {
        this.socket.removeEventListener("open", onOpen);
        this.socket.removeEventListener("error", onError);
        resolve();
      };
      const onError = () => {
        this.socket.removeEventListener("open", onOpen);
        this.socket.removeEventListener("error", onError);
        reject(new ApiError("WebSocket connection failed.", 0));
      };
      this.socket.addEventListener("open", onOpen);
      this.socket.addEventListener("error", onError);
    });
    this.socket.addEventListener("message", (event) => this.handleMessage(event.data));
    this.socket.addEventListener("close", () => this.rejectAllPending(new ApiError("WebSocket disconnected.", 0)));
  }

  async ready(): Promise<void> {
    await this.readyPromise;
  }

  async submitAction(payload: HumanActionRequest): Promise<ActionResolution> {
    return this.send<ActionResolution>({
      op: "action",
      actionType: payload.actionType,
      amount: payload.amount
    });
  }

  async nextHand(): Promise<SessionState> {
    return this.send<SessionState>({ op: "next_hand" });
  }

  async rebuy(): Promise<SessionState> {
    return this.send<SessionState>({ op: "rebuy" });
  }

  close(): void {
    this.rejectAllPending(new ApiError("WebSocket closed.", 0));
    this.socket.close();
  }

  isConnected(): boolean {
    return this.socket.readyState === WebSocket.OPEN;
  }

  private async send<T>(body: Record<string, unknown>): Promise<T> {
    await this.ready();
    if (!this.isConnected()) {
      throw new ApiError("WebSocket not connected.", 0);
    }

    const requestId = `ws-${Date.now()}-${this.requestCounter++}`;
    const payload = { ...body, requestId };

    return new Promise<T>((resolve, reject) => {
      const timeoutId = window.setTimeout(() => {
        this.pending.delete(requestId);
        reject(new ApiError("WebSocket request timed out.", 504));
      }, 10000);

      this.pending.set(requestId, {
        resolve: resolve as (value: unknown) => void,
        reject,
        timeoutId
      });
      this.socket.send(JSON.stringify(payload));
    });
  }

  private handleMessage(raw: unknown): void {
    if (typeof raw !== "string") {
      return;
    }

    let parsed: SocketMessage;
    try {
      parsed = JSON.parse(raw) as SocketMessage;
    } catch {
      return;
    }

    const requestId = parsed.requestId;
    if (!requestId) {
      return;
    }

    const pending = this.pending.get(requestId);
    if (!pending) {
      return;
    }
    this.pending.delete(requestId);
    window.clearTimeout(pending.timeoutId);

    if (parsed.type === "error") {
      const message = parsed.message ?? "WebSocket request failed.";
      pending.reject(new ApiError(message, parsed.status ?? 500));
      return;
    }

    pending.resolve(parsed.payload);
  }

  private rejectAllPending(error: ApiError): void {
    for (const [requestId, pending] of this.pending.entries()) {
      this.pending.delete(requestId);
      window.clearTimeout(pending.timeoutId);
      pending.reject(error);
    }
  }
}

export const pokerApi = new PokerApiClient();

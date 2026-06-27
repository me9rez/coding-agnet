/** Gateway client — connects to Python WebSocket gateway. */

import type { GatewayEvent, GatewayRequest } from "./gatewayTypes.js";

const DEFAULT_WS_URL = "ws://127.0.0.1:8765";

export class GatewayClient {
  #ws: WebSocket | null = null;
  #onEvent: ((event: GatewayEvent) => void) | null = null;
  #onClose: ((code: number) => void) | null = null;

  private readonly url: string;

  constructor(url?: string) {
    this.url = url ?? process.env.CODING_AGENT_WS_URL ?? DEFAULT_WS_URL;
  }

  connect(): void {
    const ws = new WebSocket(this.url);
    this.#ws = ws;

    ws.onmessage = (msg: MessageEvent) => {
      try {
        const event = JSON.parse(msg.data) as GatewayEvent;
        this.#onEvent?.(event);
      } catch {
        // Non-JSON messages (e.g. server startup noise)
      }
    };

    ws.onclose = (ev: CloseEvent) => {
      this.#ws = null;
      this.#onClose?.(ev.code);
    };

    ws.onerror = () => {
      // WebSocket errors are also followed by onclose
    };
  }

  onEvent(cb: (event: GatewayEvent) => void): void {
    this.#onEvent = cb;
  }

  onClose(cb: (code: number) => void): void {
    this.#onClose = cb;
  }

  send(request: GatewayRequest): void {
    if (this.#ws?.readyState === WebSocket.OPEN) {
      this.#ws.send(JSON.stringify(request));
    }
  }

  close(): void {
    if (this.#ws) {
      this.#ws.close();
      this.#ws = null;
    }
  }
}

/** Gateway event types — emitted by the Python gateway, consumed by the TUI. */

export interface GatewayThinkingDelta {
  type: "thinking_delta";
  delta: string;
}

export interface GatewayTextDelta {
  type: "text_delta";
  delta: string;
}

export interface GatewayToolCallStart {
  type: "tool_call_start";
  callId: string;
  name: string;
  arguments: string;
  output?: string;
}

export interface GatewayToolExecutionStart {
  type: "tool_execution_start";
  callId: string;
  name: string;
}

export interface GatewayToolExecutionDelta {
  type: "tool_execution_delta";
  callId: string;
  line: string;
}

export interface GatewayToolExecutionEnd {
  type: "tool_execution_end";
  name: string;
  callId: string;
  ok: boolean;
  result?: string;
  exitCode?: number;
  error?: string;
}

export interface GatewayTurnEnd {
  type: "turn_end";
  reason: string;
}

export interface GatewayDone {
  type: "done";
}

export interface GatewayError {
  type: "error";
  message: string;
  recoverable: boolean;
}

export interface GatewayReady {
  type: "ready";
}

export type GatewayEvent =
  | GatewayThinkingDelta
  | GatewayTextDelta
  | GatewayToolCallStart
  | GatewayToolExecutionStart
  | GatewayToolExecutionDelta
  | GatewayToolExecutionEnd
  | GatewayTurnEnd
  | GatewayDone
  | GatewayError
  | GatewayReady;

export type GatewayRequest =
  | { method: "prompt"; params: { text: string } }
  | { method: "cancel"; params: Record<string, never> };

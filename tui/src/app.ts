/**
 * App component — agent console with collapsible messages and token bar.
 *
 * Uses @simon_he/vue-tui absolute-positioning components (x, y, w, h).
 * Thinking blocks and tool calls are collapsible; token usage is shown at bottom.
 */

import type { Component, VNode } from "vue";
import { defineComponent, h, onMounted, onUnmounted, shallowRef } from "vue";
import { TBox, TText, TView } from "@simon_he/vue-tui";
import type { GatewayEvent } from "./gatewayTypes.js";
import { GatewayClient } from "./gatewayClient.js";

const COLS = 100;
const ROWS = 30;
const TOKENS_PER_CHAR = 4;

export const App: Component = defineComponent({
  setup() {
    const transcript = shallowRef<GatewayEvent[]>([]);
    const streaming = shallowRef("");
    const inputBuffer = shallowRef("");
    const activeToolCall = shallowRef<{ callId: string; name: string; arguments: string; output: string } | null>(null);
    const running = shallowRef(false);
    const collapsed = shallowRef(new Set<string>());
    const totalTokens = shallowRef(0);
    const scrollY = shallowRef(0);
    const autoScroll = shallowRef(true);
    const gw = new GatewayClient();

    /* ── Helpers ───────────────────────────────────────────── */

    function flushStreaming() {
      if (streaming.value) {
        totalTokens.value += Math.ceil(streaming.value.length / TOKENS_PER_CHAR);
        transcript.value = [...transcript.value, { type: "text_delta" as const, delta: streaming.value }];
        streaming.value = "";
      }
    }

    function flushToolCall(result?: string): void {
      const tc = activeToolCall.value;
      if (!tc) return;
      const outputStr = result ?? tc.output.trimEnd();
      const summary = { type: "tool_call_start" as const, callId: tc.callId, name: tc.name, arguments: tc.arguments, output: outputStr };
      transcript.value = [...transcript.value, summary];
      activeToolCall.value = null;
    }

    function toggleCollapse(key: string) {
      const s = new Set(collapsed.value);
      if (s.has(key)) s.delete(key);
      else s.add(key);
      collapsed.value = s;
    }

    function scrollBy(delta: number) {
      autoScroll.value = false;
      scrollY.value = Math.max(0, scrollY.value + delta);
    }

    function scrollToBottom() {
      autoScroll.value = true;
    }

    function makeKey(index: number, type: string): string {
      return `${index}-${type}`;
    }
    function handleEvent(event: GatewayEvent) {
      switch (event.type) {
        case "text_delta":
          streaming.value += event.delta;
          break;
        case "thinking_delta":
          transcript.value = [...transcript.value, event];
          break;
        case "tool_call_start":
          flushStreaming();
          flushToolCall();
          activeToolCall.value = { callId: event.callId, name: event.name, arguments: event.arguments, output: "" };
          break;
        case "tool_execution_delta":
          if (activeToolCall.value && activeToolCall.value.callId === event.callId) {
            activeToolCall.value = { ...activeToolCall.value, output: activeToolCall.value.output + event.line + "\n" };
          }
          break;
        case "tool_execution_start":
          flushStreaming();
          break;
        case "tool_execution_end":
          flushToolCall(event.result);
          break;
        case "turn_end":
          if (event.reason === "tool_calls") { flushToolCall(); break; }
          flushStreaming();
          running.value = false;
          break;
        case "done":
          flushStreaming();
          running.value = false;
          break;
        case "error":
          flushStreaming();
          transcript.value = [...transcript.value, event];
          running.value = false;
          break;
      }
    }

    function sendPrompt() {
      const text = inputBuffer.value.trim();
      if (!text || running.value) return;
      transcript.value = [...transcript.value, { type: "text_delta" as const, delta: `> ${text}` }];
      inputBuffer.value = "";
      running.value = true;
      streaming.value = "";
      gw.send({ method: "prompt", params: { text } });
    }

    function handleKeydown(e: { key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean; preventDefault: () => void }): void {
      // Scroll keys — work regardless of running state
      if (e.key === "PageUp") { scrollBy(-12); e.preventDefault(); return; }
      if (e.key === "PageDown") { scrollBy(12); e.preventDefault(); return; }
      if (e.key === "ArrowUp") { scrollBy(-1); e.preventDefault(); return; }
      if (e.key === "ArrowDown") { scrollBy(1); e.preventDefault(); return; }
      if ((e.key === "End") && (e.ctrlKey || e.metaKey)) { scrollToBottom(); e.preventDefault(); return; }
      if ((e.key === "Home") && (e.ctrlKey || e.metaKey)) { scrollBy(-9999); e.preventDefault(); return; }

      // Ctrl+C to exit
      if (e.ctrlKey && e.key.toLowerCase() === "c") { gw.close(); return; }

      // No input while agent is running
      if (running.value) return;

      // Input handling
      if (e.key === "Enter") { sendPrompt(); e.preventDefault(); return; }
      if (e.key === "Backspace") { inputBuffer.value = inputBuffer.value.slice(0, -1); e.preventDefault(); return; }
      if (!e.ctrlKey && !e.metaKey && !e.altKey && e.key.length === 1) { inputBuffer.value += e.key; e.preventDefault(); }
    }

    function handleWheel(e: { deltaY?: number; preventDefault: () => void }): void {
      if (e.deltaY) {
        scrollBy(e.deltaY > 0 ? 6 : -6);
        e.preventDefault();
      }
    }

    onMounted(() => {
      gw.onEvent(handleEvent);
      gw.connect();
    });

    onUnmounted(() => {
      gw.close();
    });

    /* ── Render ────────────────────────────────────────────── */

    /** Estimate the number of terminal rows a string occupies when wrapped. */
    function wrappedLines(text: string, width: number): number {
      if (!text || width <= 0) return 1;
      let total = 0;
      for (const line of text.split("\n")) {
        if (line.length === 0) total += 1;
        else total += Math.ceil(line.length / width);
      }
      return Math.max(1, total);
    }

    return () => {
      const nodes: VNode[] = [];

      // Title (fixed at top)
      nodes.push(h(TBox, { x: 0, y: 0, w: COLS, h: 1, border: false, key: "title" }, {
        default: () => h(TText, { x: 0, y: 0, w: COLS, value: "⚡ Coding Agent", style: { bold: true, fg: "cyan" } }),
      }));

      // Separator
      nodes.push(h(TBox, { x: 0, y: 1, w: COLS, h: 1, border: false, key: "sep" }, {
        default: () => h(TText, { x: 0, y: 0, w: COLS, value: "─".repeat(COLS), style: { dim: true } }),
      }));

      // Build scrollable content
      const areaH = ROWS - 4; // rows left for content area
      const contentNodes: VNode[] = [];
      let cy = 0;

      // Messages
      for (let i = 0; i < transcript.value.length; i++) {
        const raw = transcript.value[i];
        if (!raw) continue;
        const ev: GatewayEvent = raw;
        const msgNodes: VNode[] = [];
        let isCollapsible = false;
        let collapseKey = "";
        let delta = "";
        let msgName = "";
        let msgOk = false;
        let msgError = "";
        let msgMessage = "";
        if (ev.type === "text_delta") {
          delta = ev.delta;
          const isUser = delta.startsWith("> ");
          const label = isUser ? "You" : "Agent";
          const color = isUser ? "green" : "cyan";
          const text = isUser ? delta.slice(2) : delta;
          const textW = COLS - 2;
          const textRows = wrappedLines(text, textW);
          msgNodes.push(
            h(TText, { x: 0, y: 0, w: COLS, value: `${label}:`, style: { bold: true, fg: color } }),
            h(TText, { x: 2, y: 1, w: textW, h: textRows, value: text, wrap: true }),
          );
        } else if (ev.type === "thinking_delta") {
          delta = ev.delta;
          isCollapsible = true;
          collapseKey = makeKey(i, "think");
          const isColl = collapsed.value.has(collapseKey);
          const icon = isColl ? "▸" : "▾";
          msgNodes.push(
            h(TText, { x: 0, y: 0, w: COLS, value: `${icon} Thinking`, style: { bold: true, fg: "magenta" } }),
          );
          if (!isColl) {
            msgNodes.push(
              h(TText, { x: 2, y: 1, w: COLS - 2, value: delta, wrap: true, style: { dim: true, fg: "magenta" } }),
            );
          }
        } else if (ev.type === "tool_call_start") {
          msgName = ev.name;
          const args = ev.arguments;
          const output = (ev as any).output || "";
          isCollapsible = true;
          collapseKey = makeKey(i, "toolcall");
          const isColl = collapsed.value.has(collapseKey);
          const icon = isColl ? "▸" : "▾";
          const lines: VNode[] = [
            h(TText, { x: 0, y: 0, w: COLS, value: `${icon} 🔧 ${msgName}`, style: { fg: "yellow" } }),
          ];
          if (!isColl) {
            let yOff = 1;
            if (args && args !== "{}") {
              const argRows = wrappedLines(args, COLS - 2);
              lines.push(h(TText, { x: 2, y: yOff, w: COLS - 2, h: argRows, value: args, wrap: true, style: { fg: "cyan", dim: true } }));
              yOff += argRows;
            }
            if (output) {
              const outRows = wrappedLines(output, COLS - 2);
              lines.push(h(TText, { x: 2, y: yOff, w: COLS - 2, h: outRows, value: output, wrap: true, style: { dim: true } }));
            }
          }
          msgNodes.push(...lines);
        } else if (ev.type === "tool_execution_start") {
          msgName = ev.name;
          isCollapsible = true;
          collapseKey = makeKey(i, "tool");
          const isColl = collapsed.value.has(collapseKey);
          const icon = isColl ? "▸" : "▾";
          msgNodes.push(
            h(TText, { x: 0, y: 0, w: COLS, value: `${icon} 🔧 ${msgName}`, style: { fg: "yellow" } }),
          );
          if (!isColl) {
            msgNodes.push(
              h(TText, { x: 2, y: 1, w: COLS - 2, value: "running...", style: { dim: true } }),
            );
          }
        } else if (ev.type === "tool_execution_end") {
          msgName = ev.name;
          msgOk = ev.ok;
          msgError = ev.error ?? "";
          const status = msgOk ? "✅ done" : `❌ failed: ${msgError}`;
          const color = msgOk ? "green" : "red";
          msgNodes.push(
            h(TText, { x: 0, y: 0, w: COLS, value: `🔧 ${msgName} — ${status}`, style: { fg: color } }),
          );
        } else if (ev.type === "error") {
          msgMessage = ev.message;
          msgNodes.push(
            h(TText, { x: 0, y: 0, w: COLS, value: "\u26A0 Error: " + msgMessage, style: { fg: "red" } }),
          );
        }
        if (msgNodes.length > 0) {
          const key = collapseKey || `msg-${i}`;
          let hh = msgNodes.length;
          if (ev.type === "text_delta") {
            const textW = COLS - 2;
            const text = ev.delta.startsWith("> ") ? ev.delta.slice(2) : ev.delta;
            hh = 1 + wrappedLines(text, textW);
          } else if (ev.type === "thinking_delta" && !collapsed.value.has(collapseKey) && ev.delta) {
            hh = 1 + wrappedLines(ev.delta, COLS - 2);
          } else if (ev.type === "tool_call_start" && !collapsed.value.has(collapseKey)) {
            const args = ev.arguments && ev.arguments !== "{}" ? wrappedLines(ev.arguments, COLS - 2) : 0;
            const output = ev.output ? wrappedLines(ev.output, COLS - 2) : 0;
            hh = 1 + args + output;
          }
          contentNodes.push(h(TBox, { x: 0, y: cy, w: COLS, h: hh, border: false, key }, {
            default: () => msgNodes,
          }));
          cy += hh;
        }
      }

      // Streaming (inside scrollable area)
      if (streaming.value) {
        const streamW = COLS - 2;
        const streamH = wrappedLines(streaming.value, streamW);
        contentNodes.push(h(TBox, { x: 0, y: cy, w: COLS, h: 1 + streamH, border: false, key: "streaming" }, {
          default: () => [
            h(TText, { x: 0, y: 0, w: COLS, value: "Agent:", style: { bold: true, fg: "cyan" } }),
            h(TText, { x: 2, y: 1, w: streamW, h: streamH, value: streaming.value, wrap: true }),
          ],
        }));
        cy += 1 + streamH;
      }

      // Active tool call (inside scrollable area)
      if (activeToolCall.value) {
        const tc = activeToolCall.value;
        const tcW = COLS - 2;
        const argRows = tc.arguments && tc.arguments !== "{}" ? wrappedLines(tc.arguments, tcW) : 0;
        const outRows = tc.output ? wrappedLines(tc.output, tcW) : 0;
        const tcH = 1 + argRows + outRows;
        const tcChildren: VNode[] = [
          h(TText, { x: 0, y: 0, w: COLS, value: "▾ 🔧 " + tc.name, style: { fg: "yellow" } }),
        ];
        let tcY = 1;
        if (argRows > 0) {
          tcChildren.push(h(TText, { x: 2, y: tcY, w: tcW, h: argRows, value: tc.arguments, wrap: true, style: { fg: "cyan", dim: true } }));
          tcY += argRows;
        }
        if (outRows > 0) {
          tcChildren.push(h(TText, { x: 2, y: tcY, w: tcW, h: outRows, value: tc.output, wrap: true, style: { dim: true } }));
        }
        contentNodes.push(h(TBox, { x: 0, y: cy, w: COLS, h: tcH, border: false, key: "activetool" }, {
          default: () => tcChildren,
        }));
        cy += tcH;
      }

      // Status (inside scrollable area)
      if (running.value) {
        contentNodes.push(h(TText, { x: 0, y: cy, w: COLS, value: "… processing", style: { dim: true }, key: "status" }));
        cy += 1;
      }

      // Scroll position management
      const contentH = cy;
      const maxScroll = Math.max(0, contentH - areaH);
      if (autoScroll.value) {
        scrollY.value = maxScroll;
      } else if (scrollY.value > maxScroll) {
        scrollY.value = maxScroll;
      }
      const effectiveScrollY = scrollY.value;
      // Scrollbar — always visible; track ░, thumb █
      const scrollLines: string[] = [];
      if (contentH > areaH) {
        const thumbSize = Math.max(1, Math.round((areaH / contentH) * areaH));
        const thumbPos = Math.round((effectiveScrollY / maxScroll) * (areaH - thumbSize));
        for (let i = 0; i < areaH; i++) {
          scrollLines.push(i >= thumbPos && i < thumbPos + thumbSize ? "█" : "░");
        }
      } else {
        for (let i = 0; i < areaH; i++) scrollLines.push("░");
      }
      const scrollbarValue = scrollLines.join("\n");
      nodes.push(h(TBox, { x: 0, y: 2, w: COLS - 1, h: areaH, border: false, scrollY: effectiveScrollY, key: "scrollarea" }, {
        default: () => contentNodes,
      }));
      nodes.push(h(TText, { x: COLS - 1, y: 2, w: 1, h: areaH, value: scrollbarValue, style: { fg: "whiteBright" }, key: "scrollbar" }));
      // Token bar (fixed)
      if (totalTokens.value > 0) {
        const bar = `tok ${totalTokens.value}`;
        nodes.push(
          h(TText, { x: 0, y: ROWS - 2, w: COLS, value: bar, style: { dim: true }, key: "tokbar" }),
        );
      }

      // Input (fixed)
      const inputLine = `> ${inputBuffer.value}█`;
      nodes.push(h(TBox, { x: 0, y: ROWS - 1, w: COLS, h: 1, border: false, key: "input" }, {
        default: () => h(TText, { x: 0, y: 0, w: COLS, value: inputLine, style: { fg: "green" } }),
      }));

      return h(TView, { x: 0, y: 0, w: COLS, h: ROWS, autoFocus: true, focusable: true, onKeydownCapture: handleKeydown, onWheelCapture: handleWheel }, () =>
        h(TBox, { x: 0, y: 0, w: COLS, h: ROWS, border: false, style: { bg: "black" } }, {
          default: () => nodes,
        }),
      );
    };
  },
});

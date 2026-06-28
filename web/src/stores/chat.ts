import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { gatewayService } from '@/services/gateway'
import type { MessageContent, SessionData, UiMessage } from '@/types/session'
import {
  isDoneEvent,
  isErrorEvent,
  isTextDeltaEvent,
  isThinkingDeltaEvent,
  isToolApprovalRequestEvent,
  isToolCallStartEvent,
  isToolExecutionDeltaEvent,
  isToolExecutionEndEvent,
  isToolExecutionStartEvent,
  isTurnEndEvent,
} from '@/types/gateway'
import { generateId } from '@/utils/uid'

export type RunState = 'idle' | 'running' | 'waiting_approval'

export interface PendingApproval {
  callId: string
  name: string
  arguments: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<UiMessage[]>([])
  const runState = ref<RunState>('idle')
  const error = ref<string | null>(null)
  const pendingApprovals = ref<PendingApproval[]>([])

  const isRunning = computed(() => runState.value === 'running' || runState.value === 'waiting_approval')

  function reset() {
    messages.value = []
    runState.value = 'idle'
    error.value = null
    pendingApprovals.value = []
  }

  function addPendingApproval(approval: PendingApproval) {
    // The model paused for tool approval instead of streaming text, so discard
    // the empty loading assistant bubble created when the run started.
    const last = messages.value[messages.value.length - 1]
    if (
      last &&
      last.role === 'assistant' &&
      last.loading &&
      !last.content.trim() &&
      !last.thinking?.trim()
    ) {
      messages.value.pop()
    }
    pendingApprovals.value.push(approval)
    runState.value = 'waiting_approval'
  }

  function removePendingApproval(callId: string) {
    pendingApprovals.value = pendingApprovals.value.filter((a) => a.callId !== callId)
    if (pendingApprovals.value.length === 0 && runState.value === 'waiting_approval') {
      runState.value = 'running'
    }
  }

  function sendApprovalResponse(callId: string, approved: boolean, remember = false) {
    gatewayService.sendApprovalResponse(callId, approved, remember)
    removePendingApproval(callId)
  }

  function loadSession(session: SessionData) {
    messages.value = convertBackendMessages(session.messages)
  }

  function addUserMessage(text: string) {
    messages.value.push({
      id: generateId('msg'),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    })
  }

  function ensureAssistantMessage(): UiMessage {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant' && !last.toolCall && !last.toolExecution) {
      return last
    }
    const msg: UiMessage = {
      id: generateId('msg'),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }
    messages.value.push(msg)
    return msg
  }

  function appendTextDelta(delta: string) {
    const msg = ensureAssistantMessage()
    msg.loading = false
    msg.content += delta
  }

  function appendThinkingDelta(delta: string) {
    const msg = ensureAssistantMessage()
    msg.loading = false
    msg.thinking = (msg.thinking ?? '') + delta
  }

  function startToolCall(callId: string, name: string, args: string) {
    // Discard the empty loading assistant bubble that was created when the run
    // started, since the model decided to call a tool instead of streaming text.
    const last = messages.value[messages.value.length - 1]
    if (
      last &&
      last.role === 'assistant' &&
      last.loading &&
      !last.content.trim() &&
      !last.thinking?.trim()
    ) {
      messages.value.pop()
    }
    messages.value.push({
      id: generateId('tool'),
      role: 'tool',
      content: '',
      timestamp: Date.now(),
      toolCall: { callId, name, arguments: args },
    })
  }

  function startToolExecution(callId: string, name: string) {
    const tool = findToolMessage(callId)
    if (tool) {
      tool.toolExecution = { callId, name, output: '', ok: false, exitCode: 0, finished: false }
    } else {
      messages.value.push({
        id: generateId('tool'),
        role: 'tool',
        content: '',
        timestamp: Date.now(),
        toolExecution: { callId, name, output: '', ok: false, exitCode: 0, finished: false },
      })
    }
  }

  function findToolMessage(callId: string): UiMessage | undefined {
    return messages.value.find(
      (m) => m.role === 'tool' && (m.toolCall?.callId === callId || m.toolExecution?.callId === callId),
    )
  }

  function appendToolExecutionDelta(callId: string, line: string) {
    const tool = findToolMessage(callId)
    if (tool?.toolExecution) {
      tool.toolExecution.output += line
    }
  }

  function endToolExecution(callId: string, name: string, ok: boolean, exitCode: number) {
    const tool = findToolMessage(callId)
    if (tool) {
      if (!tool.toolExecution) {
        tool.toolExecution = { callId, name, output: '', ok, exitCode, finished: true }
      } else {
        tool.toolExecution.ok = ok
        tool.toolExecution.exitCode = exitCode
        tool.toolExecution.finished = true
      }
    }
  }

  function sendMessage(text: string, sessionId?: string) {
    if (!text.trim()) return
    addUserMessage(text)
    runState.value = 'running'
    error.value = null
    messages.value.push({
      id: generateId('msg'),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      loading: true,
    })
    gatewayService.sendPrompt(text, sessionId)
  }

  function stop() {
    gatewayService.cancel()
  }

  function setupEventListeners() {
    gatewayService.on('text_delta', (event) => {
      if (isTextDeltaEvent(event)) appendTextDelta(event.delta)
    })
    gatewayService.on('thinking_delta', (event) => {
      if (isThinkingDeltaEvent(event)) appendThinkingDelta(event.delta)
    })
    gatewayService.on('tool_call_start', (event) => {
      if (isToolCallStartEvent(event)) startToolCall(event.callId, event.name, event.arguments)
    })
    gatewayService.on('tool_execution_start', (event) => {
      if (isToolExecutionStartEvent(event)) {
        startToolExecution(event.callId, event.name)
      }
    })
    gatewayService.on('tool_execution_delta', (event) => {
      if (isToolExecutionDeltaEvent(event)) appendToolExecutionDelta(event.callId, event.line)
    })
    gatewayService.on('tool_execution_end', (event) => {
      if (isToolExecutionEndEvent(event)) endToolExecution(event.callId, event.name, event.ok, event.exitCode)
    })
    gatewayService.on('turn_end', (event) => {
      if (isTurnEndEvent(event) && event.reason === 'complete') {
        // assistant message naturally complete
      }
    })
    gatewayService.on('done', () => {
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant') {
        last.loading = false
      }
      runState.value = 'idle'
    })
    gatewayService.on('error', (event) => {
      if (isErrorEvent(event)) {
        if (!event.recoverable) {
          const last = messages.value[messages.value.length - 1]
          if (last && last.role === 'assistant') {
            last.loading = false
          }
          runState.value = 'idle'
        }
        error.value = event.message
      }
    })
    gatewayService.on('tool_approval_request', (event) => {
      if (isToolApprovalRequestEvent(event)) {
        addPendingApproval({
          callId: event.callId,
          name: event.name,
          arguments: event.arguments,
        })
      }
    })
  }

  return {
    messages,
    runState,
    isRunning,
    error,
    pendingApprovals,
    reset,
    loadSession,
    sendMessage,
    stop,
    setupEventListeners,
    sendApprovalResponse,
  }
})

function isTextContent(content: MessageContent): content is Extract<MessageContent, { type: 'text' }> {
  return content.type === 'text'
}

function isFunctionCallContent(content: MessageContent): content is Extract<MessageContent, { type: 'function_call' }> {
  return content.type === 'function_call'
}

function isFunctionResultContent(content: MessageContent): content is Extract<MessageContent, { type: 'function_result' }> {
  return content.type === 'function_result'
}

function isUsageContent(content: MessageContent): content is Extract<MessageContent, { type: 'usage' }> {
  return content.type === 'usage'
}

interface BackendMessage {
  role: string
  contents: MessageContent[]
  thinking?: string
  additional_properties?: Record<string, unknown>
}

export function convertBackendMessages(msgs: BackendMessage[]): UiMessage[] {
  const result: UiMessage[] = []
  const toolMessages = new Map<string, UiMessage>()
  let textSegment: { role: string; content: string; thinking?: string } | null = null

  function flushText() {
    if (!textSegment) return
    const hasContent = textSegment.content.trim().length > 0
    const hasThinking = !!textSegment.thinking && textSegment.thinking.trim().length > 0
    if (!hasContent && !hasThinking) {
      textSegment = null
      return
    }
    result.push({
      id: generateId('msg'),
      role: textSegment.role as 'user' | 'assistant' | 'tool',
      content: textSegment.content,
      timestamp: Date.now(),
      thinking: textSegment.thinking,
    })
    textSegment = null
  }

  for (const msg of msgs) {
    const thinking = typeof msg.thinking === 'string'
      ? msg.thinking
      : typeof msg.additional_properties?.thinking === 'string'
        ? msg.additional_properties.thinking
        : undefined
    for (const content of msg.contents) {
      if (isTextContent(content)) {
        if (!textSegment) {
          textSegment = { role: msg.role, content: '', thinking }
        } else if (textSegment.role !== msg.role) {
          flushText()
          textSegment = { role: msg.role, content: '', thinking }
        }
        textSegment.content += content.text ?? ''
        continue
      }

      if (isUsageContent(content)) {
        // Usage blocks are for accounting only and should not be rendered.
        continue
      }

      flushText()

      if (isFunctionCallContent(content)) {
        const callId = content.call_id ?? ''
        const existing = toolMessages.get(callId)
        if (existing) {
          existing.toolCall = {
            callId,
            name: content.name ?? '',
            arguments: content.arguments ?? '',
          }
        } else {
          const toolMsg: UiMessage = {
            id: generateId('tool'),
            role: 'tool',
            content: '',
            timestamp: Date.now(),
            toolCall: {
              callId,
              name: content.name ?? '',
              arguments: content.arguments ?? '',
            },
          }
          toolMessages.set(callId, toolMsg)
          result.push(toolMsg)
        }
      } else if (isFunctionResultContent(content)) {
        const callId = content.call_id ?? ''
        const existing = toolMessages.get(callId)
        if (existing) {
          existing.toolExecution = {
            callId,
            name: content.name ?? '',
            output: content.result ?? '',
            ok: true,
            exitCode: 0,
            finished: true,
          }
        } else {
          const toolMsg: UiMessage = {
            id: generateId('tool'),
            role: 'tool',
            content: '',
            timestamp: Date.now(),
            toolExecution: {
              callId,
              name: content.name ?? '',
              output: content.result ?? '',
              ok: true,
              exitCode: 0,
              finished: true,
            },
          }
          toolMessages.set(callId, toolMsg)
          result.push(toolMsg)
        }
      }
    }

    // Ensure a message with only thinking (no text/tool) still surfaces the thinking block,
    // but do not create empty user/tool bubbles.
    if (thinking && !textSegment && msg.role === 'assistant') {
      textSegment = { role: msg.role, content: '', thinking }
    }
    flushText()
  }

  flushText()
  return result
}

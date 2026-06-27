export interface SessionInfo {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
}

export interface SessionData {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: Message[]
}

export interface ModelConfig {
  id: string
  name: string
  contextWindow?: number
  maxTokens?: number
  reasoning?: boolean
  thinking_level?: string[]
  input?: string[]
}

export interface ProviderConfig {
  api?: string
  baseUrl?: string
  apiKey?: string
  models: ModelConfig[]
}

export interface Settings {
  selectedModel: string
  providers: Record<string, ProviderConfig>
  max_turns: number
}

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

export interface TextContent {
  type: 'text'
  text: string
}

export interface FunctionCallContent {
  type: 'function_call'
  call_id: string
  name: string
  arguments: string
}

export interface FunctionResultContent {
  type: 'function_result'
  call_id: string
  name: string
  result: string
}

export type MessageContent = TextContent | FunctionCallContent | FunctionResultContent

export interface Message {
  role: MessageRole
  contents: MessageContent[]
  additional_properties?: Record<string, unknown>
}

export interface UiMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp: number
  thinking?: string
  toolCall?: {
    callId: string
    name: string
    arguments: string
  }
  toolExecution?: {
    callId: string
    name: string
    output: string
    ok: boolean
    exitCode: number
    finished?: boolean
  }
}

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { GatewayService } from '@/services/gateway'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  readyState: number = MockWebSocket.CONNECTING
  onopen: ((ev?: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev?: Event) => void) | null = null
  sent: string[] = []

  constructor() {
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({ code: 1000 } as CloseEvent)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.()
  }

  receive(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }
}

describe('GatewayService', () => {
  let originalWebSocket: typeof WebSocket

  beforeEach(() => {
    originalWebSocket = globalThis.WebSocket
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    MockWebSocket.instances = []
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('connects and emits open event', () => {
    const service = new GatewayService('ws://localhost:8765')
    let opened = false
    service.on('open', () => {
      opened = true
    })
    service.connect()
    const ws = MockWebSocket.instances[0]!
    ws.open()
    expect(opened).toBe(true)
  })

  it('sends prompt request', () => {
    const service = new GatewayService('ws://localhost:8765')
    service.connect()
    const ws = MockWebSocket.instances[0]!
    ws.open()
    service.sendPrompt('hello', 'abc')
    expect(ws.sent).toHaveLength(1)
    const req = JSON.parse(ws.sent[0]!)
    expect(req.method).toBe('prompt')
    expect(req.params).toEqual({ text: 'hello', sessionId: 'abc' })
  })

  it('resolves rpc call on rpc_response', async () => {
    const service = new GatewayService('ws://localhost:8765')
    service.connect()
    const ws = MockWebSocket.instances[0]!
    ws.open()

    const promise = service.call('listSessions')
    const sent = JSON.parse(ws.sent[0]!)
    expect(sent.method).toBe('listSessions')

    ws.receive({ type: 'rpc_response', id: sent.id, result: [{ id: '1', title: 'Chat' }] })

    const result = await promise
    expect(result).toEqual([{ id: '1', title: 'Chat' }])
  })

  it('rejects rpc call on rpc_response error', async () => {
    const service = new GatewayService('ws://localhost:8765')
    service.connect()
    const ws = MockWebSocket.instances[0]!
    ws.open()

    const promise = service.call('loadSession', { sessionId: 'missing' })
    const sent = JSON.parse(ws.sent[0]!)
    ws.receive({ type: 'rpc_response', id: sent.id, error: { message: 'Session not found' } })

    await expect(promise).rejects.toThrow('Session not found')
  })
})

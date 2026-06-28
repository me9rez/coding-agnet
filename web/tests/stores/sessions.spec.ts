import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { gatewayService } from '@/services/gateway'
import { useSessionsStore } from '@/stores/sessions'

vi.mock('@/services/gateway', () => ({
  gatewayService: {
    call: vi.fn(),
  },
}))

describe('useSessionsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(gatewayService.call).mockReset()
  })

  it('fetches sessions', async () => {
    vi.mocked(gatewayService.call).mockResolvedValueOnce([
      { id: '1', title: 'Chat 1', createdAt: '2024-01-01', updatedAt: '2024-01-02', messageCount: 3 },
    ])

    const store = useSessionsStore()
    await store.fetchSessions()

    expect(store.sessions).toHaveLength(1)
    expect(store.sessions[0]?.title).toBe('Chat 1')
  })

  it('creates a session and selects it', async () => {
    vi.mocked(gatewayService.call)
      .mockResolvedValueOnce({ id: '2', title: 'New Chat', messages: [], createdAt: '', updatedAt: '' })
      .mockResolvedValueOnce([])

    const store = useSessionsStore()
    const session = await store.createSession('New Chat')

    expect(session?.id).toBe('2')
    expect(store.currentSessionId).toBe('2')
  })

  it('deletes a session and clears selection', async () => {
    vi.mocked(gatewayService.call)
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce([])

    const store = useSessionsStore()
    store.currentSessionId = '3'
    await store.deleteSession('3')

    expect(store.currentSessionId).toBeNull()
  })
})

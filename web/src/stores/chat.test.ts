import { describe, expect, it } from 'vitest'
import { convertBackendMessages } from './chat'

describe('convertBackendMessages', () => {
  it('keeps consecutive user messages separate', () => {
    const msgs = [
      { role: 'user', contents: [{ type: 'text' as const, text: '第一条' }] },
      { role: 'user', contents: [{ type: 'text' as const, text: '第二条' }] },
    ]
    const result = convertBackendMessages(msgs)
    expect(result).toHaveLength(2)
    expect(result[0]!.content).toBe('第一条')
    expect(result[1]!.content).toBe('第二条')
  })

  it('preserves assistant thinking and skips empty bubbles', () => {
    const msgs = [
      { role: 'assistant', contents: [{ type: 'text' as const, text: '答案' }], thinking: '我先想想' },
      { role: 'assistant', contents: [{ type: 'text' as const, text: '' }] },
      { role: 'assistant', contents: [], thinking: '只有思考没有文本' },
    ]
    const result = convertBackendMessages(msgs)
    expect(result).toHaveLength(2)
    expect(result[0]!.content).toBe('答案')
    expect(result[0]!.thinking).toBe('我先想想')
    expect(result[1]!.content).toBe('')
    expect(result[1]!.thinking).toBe('只有思考没有文本')
  })

  it('merges text segments within a single backend message', () => {
    const msgs = [
      {
        role: 'assistant',
        contents: [
          { type: 'text' as const, text: '前半' },
          { type: 'text' as const, text: '后半' },
        ],
      },
    ]
    const result = convertBackendMessages(msgs)
    expect(result).toHaveLength(1)
    expect(result[0]!.content).toBe('前半后半')
  })

  it('skips usage content and avoids duplicate assistant bubbles', () => {
    const msgs = [
      {
        role: 'assistant',
        contents: [
          { type: 'text' as const, text: '答案' },
          { type: 'usage' as const, usage_details: { input_token_count: 1, output_token_count: 2, total_token_count: 3 } },
        ],
        thinking: '我先想想',
      },
    ]
    const result = convertBackendMessages(msgs as any)
    expect(result).toHaveLength(1)
    expect(result[0]!.content).toBe('答案')
    expect(result[0]!.thinking).toBe('我先想想')
  })
})

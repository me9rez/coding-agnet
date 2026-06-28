import { describe, expect, it } from 'vitest'
import { convertBackendMessages } from '@/stores/chat'

describe('convertBackendMessages — wire payload from gateway', () => {
  it('Case A: assistant with text + top-level thinking (post-fix wire format)', () => {
    const wire = [
      { role: 'user', contents: [{ type: 'text', text: '请回答' }] },
      {
        role: 'assistant',
        contents: [{ type: 'text', text: '这里是答案' }],
        thinking: '我先想了三秒钟',
      },
    ]
    const out = convertBackendMessages(wire as any)
    expect(out).toHaveLength(2)
    expect(out[1]!.content).toBe('这里是答案')
    expect(out[1]!.thinking).toBe('我先想了三秒钟')
  })

  it('Case B: assistant with thinking only', () => {
    const wire = [
      { role: 'user', contents: [{ type: 'text', text: '?' }] },
      {
        role: 'assistant',
        contents: [],
        thinking: '只有思考没有文本',
      },
    ]
    const out = convertBackendMessages(wire as any)
    expect(out).toHaveLength(2)
    expect(out[1]!.content).toBe('')
    expect(out[1]!.thinking).toBe('只有思考没有文本')
  })

  it('Case C: assistant with tool call + text + thinking (mixed)', () => {
    const wire = [
      { role: 'user', contents: [{ type: 'text', text: '查一下' }] },
      {
        role: 'assistant',
        contents: [
          { type: 'function_call', call_id: 'c1', name: 'run_command', arguments: '{"command":"ls"}' },
          { type: 'function_result', call_id: 'c1', name: 'run_command', result: 'a.txt\nb.txt' },
          { type: 'text', text: '文件有 a.txt 和 b.txt' },
        ],
        thinking: '先列目录',
      },
    ]
    const out = convertBackendMessages(wire as any)
    const assistant = out.find((m: any) => m.role === 'assistant' && m.thinking)
    expect(assistant, 'expected assistant bubble with thinking').toBeTruthy()
    expect(assistant!.thinking).toBe('先列目录')
  })

  it('Case D: assistant with function_call + thinking (no text) — thinking before tool', () => {
    const wire = [
      { role: 'user', contents: [{ type: 'text', text: '试试list_directory' }] },
      {
        role: 'assistant',
        contents: [
          { type: 'function_call', call_id: 'c1', name: 'list_directory', arguments: '{}' },
        ],
        thinking: '先想一想再调用工具',
      },
      {
        role: 'tool',
        contents: [
          { type: 'function_result', call_id: 'c1', name: 'list_directory', result: 'a\nb' },
        ],
      },
      {
        role: 'assistant',
        contents: [
          { type: 'text', text: '已经列出来了' },
        ],
      },
    ]
    const out = convertBackendMessages(wire as any)
    // Order must be: user → assistant(thinking before tool) → tool → assistant(text)
    expect(out).toHaveLength(4)
    expect(out[0]!.role).toBe('user')
    expect(out[1]!.role).toBe('assistant')
    expect(out[1]!.thinking).toBe('先想一想再调用工具')
    expect(out[1]!.content).toBe('')
    expect(out[2]!.role).toBe('tool')
    expect(out[3]!.role).toBe('assistant')
    expect(out[3]!.thinking).toBeUndefined()
    expect(out[3]!.content).toBe('已经列出来了')
  })
})

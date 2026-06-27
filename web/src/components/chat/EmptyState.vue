<script setup lang="ts">
import { Sparkles, Terminal } from '@lucide/vue'
import { useSessionsStore } from '@/stores/sessions'

const sessionsStore = useSessionsStore()

const emit = defineEmits<{
  useSuggestion: [text: string]
}>()

async function handleNewChat() {
  await sessionsStore.createSession('新对话')
}

function useSuggestion(text: string) {
  emit('useSuggestion', text)
}

const suggestions = [
  { icon: Terminal, text: '运行 ls 命令试试' },
  { icon: Sparkles, text: '帮我写一个 Python 脚本' },
]
</script>

<template>
  <div class="flex-1 flex flex-col items-center justify-center text-center px-8">
    <div class="w-16 h-16 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)] flex items-center justify-center mb-5 shadow-[var(--shadow)]">
      <Sparkles class="w-8 h-8 text-[var(--text-muted)]" />
    </div>
    <h2 class="text-xl font-medium mb-2">
      Coding Agent
    </h2>
    <p class="text-sm text-[var(--text-muted)] mb-6 max-w-md">
      选择一个现有会话继续对话，或开始新的任务。
    </p>

    <div class="flex flex-wrap items-center justify-center gap-3 mb-6">
      <button
        v-for="(s, idx) in suggestions"
        :key="idx"
        class="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-sm text-[var(--text-muted)] hover:border-[var(--text-subtle)] hover:text-[var(--text)] transition shadow-[var(--shadow)]"
        @click="useSuggestion(s.text)"
      >
        <component :is="s.icon" class="w-4 h-4" />
        <span>{{ s.text }}</span>
      </button>
    </div>

    <button
      class="px-5 py-2.5 rounded-xl bg-[var(--text)] text-[var(--bg-card)] text-sm hover:opacity-90 transition shadow-[var(--shadow)]"
      @click="handleNewChat"
    >
      新建任务
    </button>
  </div>
</template>

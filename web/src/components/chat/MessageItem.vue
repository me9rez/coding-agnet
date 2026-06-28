<script setup lang="ts">
import { Bot } from '@lucide/vue'
import { computed } from 'vue'
import ToolCallBlock from '@/components/chat/ToolCallBlock.vue'
import type { UiMessage } from '@/types/session'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  message: UiMessage
}>()

const renderedContent = computed(() => renderMarkdown(props.message.content))
</script>

<template>
  <div
    class="flex gap-3"
    :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      v-if="message.role !== 'user'"
      class="w-8 h-8 rounded-full bg-[var(--bg-muted)] flex items-center justify-center flex-shrink-0"
    >
      <Bot class="w-4 h-4 text-[var(--text-muted)]" />
    </div>

    <div class="max-w-[85%] space-y-2">
      <div
        v-if="message.role === 'user' && message.content.trim()"
        class="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-[var(--text)] text-[var(--bg-card)] text-sm shadow-[var(--shadow)]"
      >
        {{ message.content }}
      </div>

      <div v-else-if="message.role === 'tool'" class="w-full">
        <ToolCallBlock :message="message" />
      </div>

      <div v-else-if="message.loading && !message.content.trim() && !message.thinking" class="space-y-2">
        <div class="flex items-center gap-2 text-xs text-[var(--text-subtle)]">
          <span class="font-medium text-[var(--text)]">Coding Agent</span>
          <span>·</span>
          <span>助手</span>
        </div>
        <div class="px-4 py-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)]">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-[var(--text-subtle)] animate-bounce" style="animation-delay: 0ms" />
            <span class="w-2 h-2 rounded-full bg-[var(--text-subtle)] animate-bounce" style="animation-delay: 150ms" />
            <span class="w-2 h-2 rounded-full bg-[var(--text-subtle)] animate-bounce" style="animation-delay: 300ms" />
          </div>
        </div>
      </div>

      <div v-else-if="message.thinking || message.content.trim()" class="space-y-2">
        <div class="flex items-center gap-2 text-xs text-[var(--text-subtle)]">
          <span class="font-medium text-[var(--text)]">Coding Agent</span>
          <span>·</span>
          <span>助手</span>
        </div>

        <div
          v-if="message.thinking"
          class="px-4 py-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-sm text-[var(--text-muted)] italic shadow-[var(--shadow)]"
        >
          {{ message.thinking }}
        </div>

        <div
          v-if="message.content.trim()"
          class="px-4 py-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-sm shadow-[var(--shadow)] prose prose-neutral max-w-none"
          v-html="renderedContent"
        />
      </div>
    </div>
  </div>
</template>

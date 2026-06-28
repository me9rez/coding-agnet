<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import ApprovalPanel from '@/components/ApprovalPanel.vue'
import ChatHeader from '@/components/chat/ChatHeader.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import ContextPanel from '@/components/chat/ContextPanel.vue'
import EmptyState from '@/components/chat/EmptyState.vue'
import MessageList from '@/components/chat/MessageList.vue'
import Sidebar from '@/components/chat/Sidebar.vue'
import { useChatStore } from '@/stores/chat'
import { useSessionsStore } from '@/stores/sessions'

const sessionsStore = useSessionsStore()
const chatStore = useChatStore()
const chatInputRef = ref<{ setText: (text: string) => void } | null>(null)

const currentSessionModel = computed(() => {
  if (!sessionsStore.currentSessionId) return ''
  const session = sessionsStore.sessions.find((s) => s.id === sessionsStore.currentSessionId)
  return session?.model || ''
})

async function handleUseSuggestion(text: string, model: string) {
  const session = await sessionsStore.createSession(text, model)
  if (session) {
    await nextTick()
    chatInputRef.value?.setText(text)
  }
}

watch(
  () => sessionsStore.currentSessionId,
  async (sessionId) => {
    if (sessionId) {
      const session = await sessionsStore.loadSession(sessionId)
      if (session) {
        chatStore.loadSession(session)
      }
    } else {
      chatStore.reset()
    }
  },
)

function handleSend(text: string) {
  chatStore.sendMessage(text, sessionsStore.currentSessionId ?? undefined)
}

async function handleModelChange(model: string) {
  if (sessionsStore.currentSessionId) {
    await sessionsStore.updateSessionModel(sessionsStore.currentSessionId, model)
  }
}

function handleStop() {
  chatStore.stop()
}
</script>

<template>
  <div class="h-full flex bg-[var(--bg-page)] text-[var(--text)]">
    <Sidebar class="w-64 flex-shrink-0 border-r border-[var(--border)] bg-[var(--bg-page)]" />

    <main class="flex-1 flex flex-col min-w-0 bg-[var(--bg-page)]">
      <ChatHeader />
      <MessageList
        v-if="sessionsStore.currentSessionId || chatStore.messages.length > 0"
        class="flex-1 overflow-y-auto"
      />
      <EmptyState v-else @send="handleUseSuggestion" @use-suggestion="handleUseSuggestion" />
      <div
        v-if="sessionsStore.currentSessionId || chatStore.messages.length > 0"
        class="px-4 pb-2"
      >
        <ApprovalPanel />
      </div>
      <ChatInput
        v-if="sessionsStore.currentSessionId || chatStore.messages.length > 0"
        ref="chatInputRef"
        :model="currentSessionModel"
        :disabled="chatStore.isRunning"
        @send="handleSend"
        @stop="handleStop"
        @update:model="handleModelChange"
      />
    </main>

    <ContextPanel />
  </div>
</template>

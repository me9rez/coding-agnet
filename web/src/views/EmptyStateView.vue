<script setup lang="ts">
import { useRouter } from 'vue-router'
import EmptyState from '@/components/chat/EmptyState.vue'
import { useChatStore } from '@/stores/chat'
import { useSessionsStore } from '@/stores/sessions'

const router = useRouter()
const sessionsStore = useSessionsStore()
const chatStore = useChatStore()

// Reset the chat store so the previous session's messages don't leak into the
// empty home view.
chatStore.reset()

async function navigateToSession(text: string, model: string) {
  const session = await sessionsStore.createSession(text, model)
  if (session) {
    router.push({ name: 'chat-session', params: { sessionId: session.id } })
  }
}
</script>

<template>
  <EmptyState
    class="flex-1"
    @send="navigateToSession"
    @use-suggestion="navigateToSession"
  />
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import EmptyState from '@/components/chat/EmptyState.vue'
import { useChatStore } from '@/stores/chat'
import { useSessionsStore } from '@/stores/sessions'
import { useWorkspaceStore } from '@/stores/workspace'

const router = useRouter()
const sessionsStore = useSessionsStore()
const chatStore = useChatStore()
const workspaceStore = useWorkspaceStore()

// Reset the chat store so the previous session's messages don't leak into the
// empty home view.
chatStore.reset()

async function navigateToSession(text: string, model: string) {
  const workspace = workspaceStore.workspace?.name || ''
  const session = await sessionsStore.createSession(text, model, workspace)
  if (session) {
    router.push({ name: 'chat-session', params: { sessionId: session.id }, query: { initialMessage: text } })
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

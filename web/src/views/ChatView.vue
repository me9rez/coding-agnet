<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import ChatHeader from '@/components/chat/ChatHeader.vue'
import ContextPanel from '@/components/chat/ContextPanel.vue'
import Sidebar from '@/components/chat/Sidebar.vue'
import { useSessionsStore } from '@/stores/sessions'

const sessionsStore = useSessionsStore()
const route = useRoute()

// Drive the active session from the route so the sidebar highlight and the
// chat input both agree with whatever URL the user is on.
const activeSessionId = computed<string | null>(() => {
  const id = route.params.sessionId
  if (typeof id === 'string' && id.length > 0) {
    if (sessionsStore.currentSessionId !== id) {
      sessionsStore.selectSession(id)
    }
    return id
  }
  if (sessionsStore.currentSessionId) {
    sessionsStore.clearCurrentSession()
  }
  return null
})

// Each session gets a stable, unique cache key so keep-alive can hold a
// separate instance per session. The home view uses the literal 'home' key.
const keepAliveKey = computed(() => {
  if (activeSessionId.value) {
    return `session:${activeSessionId.value}`
  }
  return 'home'
})
</script>

<template>
  <div class="h-full flex bg-[var(--bg-page)] text-[var(--text)]">
    <Sidebar class="w-64 flex-shrink-0 border-r border-[var(--border)] bg-[var(--bg-page)]" />

    <main class="flex-1 flex flex-col min-w-0 bg-[var(--bg-page)]">
      <ChatHeader />
      <RouterView v-slot="{ Component }">
        <keep-alive :max="10">
          <component :is="Component" :key="keepAliveKey" />
        </keep-alive>
      </RouterView>
    </main>

    <ContextPanel />
  </div>
</template>

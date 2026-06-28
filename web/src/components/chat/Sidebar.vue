<script setup lang="ts">
import {
  Clock,
  Folder,
  HelpCircle,
  Loader2,
  Plus,
  Settings,
  Upload,
  User,
  Wrench,
  Zap,
} from '@lucide/vue'
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { gatewayService } from '@/services/gateway'
import { useSessionsStore } from '@/stores/sessions'

const sessionsStore = useSessionsStore()

let unsubscribe: (() => void) | null = null

const editingId = ref<string | null>(null)
const editingTitle = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)
const creating = ref(false)

const contextMenu = ref<{
  show: boolean
  x: number
  y: number
  sessionId: string | null
}>({ show: false, x: 0, y: 0, sessionId: null })

async function loadSessions() {
  if (!gatewayService.isConnected()) return
  await sessionsStore.fetchSessions()
}

onMounted(() => {
  loadSessions()
  unsubscribe = gatewayService.on('open', () => {
    sessionsStore.fetchSessions()
  })
  window.addEventListener('click', closeContextMenu)
})

onUnmounted(() => {
  unsubscribe?.()
  window.removeEventListener('click', closeContextMenu)
})

async function handleNewChat() {
  if (creating.value) return
  creating.value = true
  try {
    await sessionsStore.createSession('新对话')
  } finally {
    creating.value = false
  }
}

function selectSession(id: string) {
  if (editingId.value === id) return
  sessionsStore.selectSession(id)
}

function openContextMenu(sessionId: string, event: MouseEvent) {
  if (editingId.value) return
  event.preventDefault()
  event.stopPropagation()
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    sessionId,
  }
}

function closeContextMenu() {
  contextMenu.value.show = false
  contextMenu.value.sessionId = null
}

function getSessionById(id: string | null) {
  if (!id) return null
  return sessionsStore.sessions.find((s) => s.id === id) ?? null
}

async function handleMenuRename(event: MouseEvent) {
  event.stopPropagation()
  const session = getSessionById(contextMenu.value.sessionId)
  closeContextMenu()
  if (session) {
    await startRename(session, event)
  }
}

async function handleMenuDelete(event: MouseEvent) {
  event.stopPropagation()
  const id = contextMenu.value.sessionId
  closeContextMenu()
  if (id) {
    await sessionsStore.deleteSession(id)
  }
}

async function startRename(session: { id: string; title: string }, event: MouseEvent) {
  event.stopPropagation()
  editingId.value = session.id
  editingTitle.value = session.title || ''
  await nextTick()
  const el = Array.isArray(renameInputRef.value)
    ? (renameInputRef.value[0] as HTMLInputElement | undefined)
    : renameInputRef.value
  el?.focus()
}

function cancelRename() {
  editingId.value = null
  editingTitle.value = ''
}

async function commitRename(sessionId: string) {
  const title = editingTitle.value.trim()
  if (title) {
    await sessionsStore.updateSession(sessionId, title)
  }
  editingId.value = null
  editingTitle.value = ''
}

function handleRenameKeydown(sessionId: string, event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    commitRename(sessionId)
  } else if (event.key === 'Escape') {
    cancelRename()
  }
}

function formatTime(iso: string) {
  const date = new Date(iso)
  return date.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <aside class="h-full flex flex-col bg-[var(--bg-page)]">
    <div class="p-3">
      <button
        class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-sm font-medium hover:bg-[var(--bg-muted)] transition shadow-[var(--shadow)] disabled:opacity-60"
        :disabled="creating"
        @click="handleNewChat"
      >
        <Loader2 v-if="creating" class="w-4 h-4 animate-spin" />
        <Plus v-else class="w-4 h-4" />
        <span>新建任务</span>
      </button>
    </div>

    <nav class="px-3 space-y-1">
      <a href="#" class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition">
        <Wrench class="w-4 h-4" />
        <span>工具箱</span>
      </a>
      <a href="#" class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition">
        <Zap class="w-4 h-4" />
        <span>自动化</span>
      </a>
    </nav>

    <div class="px-3 py-2">
      <div class="px-2 py-2 text-xs font-medium text-[var(--text-subtle)]">
        项目
      </div>
      <a href="#" class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition">
        <Folder class="w-4 h-4" />
        <span>cowork</span>
      </a>
    </div>

    <div class="flex-1 overflow-y-auto px-3 py-2">
      <div class="px-2 py-2 text-xs font-medium text-[var(--text-subtle)] flex items-center gap-1">
        <Clock class="w-3.5 h-3.5" />
        <span>最近</span>
      </div>

      <div v-if="sessionsStore.loading" class="px-3 py-4 text-sm text-[var(--text-muted)]">
        加载中…
      </div>
      <div
        v-else-if="sessionsStore.sessions.length === 0"
        class="px-3 py-4 text-sm text-[var(--text-muted)]"
      >
        暂无会话
      </div>
      <div
        v-if="sessionsStore.error"
        class="mx-3 mb-2 px-3 py-2 text-xs text-red-600 bg-red-50 rounded-lg border border-red-100"
      >
        {{ sessionsStore.error }}
      </div>
      <ul v-else class="space-y-1">
        <li
          v-for="session in sessionsStore.sessions"
          :key="session.id"
          class="group relative flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer transition"
          :class="{
            'bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)]': sessionsStore.currentSessionId === session.id,
            'hover:bg-[var(--bg-muted)]': sessionsStore.currentSessionId !== session.id,
          }"
          @click="selectSession(session.id)"
          @contextmenu="openContextMenu(session.id, $event)"
        >
          <div
            v-if="sessionsStore.currentSessionId === session.id"
            class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-full bg-[var(--text)]"
          />
          <div class="min-w-0 flex-1 pl-1">
            <div v-if="editingId === session.id" class="w-full">
              <input
                ref="renameInputRef"
                v-model="editingTitle"
                type="text"
                class="w-full text-sm px-2 py-1 rounded border border-[var(--border)] bg-[var(--bg-card)] outline-none focus:border-[var(--text-muted)]"
                @blur="commitRename(session.id)"
                @keydown="handleRenameKeydown(session.id, $event)"
                @click.stop
              >
            </div>
            <template v-else>
              <div
                class="truncate text-sm font-medium"
                @dblclick="startRename(session, $event)"
              >
                {{ session.title || '未命名会话' }}
              </div>
              <div class="text-xs text-[var(--text-subtle)]">
                {{ formatTime(session.updatedAt) }}
              </div>
            </template>
          </div>
        </li>
      </ul>
    </div>

    <div class="p-3 border-t border-[var(--border)] flex items-center justify-between">
      <button class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition">
        <User class="w-4 h-4" />
        <span>我</span>
      </button>
      <div class="flex items-center gap-1">
        <button class="p-2 rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition" title="上传">
          <Upload class="w-4 h-4" />
        </button>
        <RouterLink
          to="/settings"
          class="p-2 rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition"
          title="设置"
        >
          <Settings class="w-4 h-4" />
        </RouterLink>
        <button class="p-2 rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition" title="帮助">
          <HelpCircle class="w-4 h-4" />
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="contextMenu.show"
        class="fixed z-50 min-w-[120px] rounded-xl border border-[var(--border)] bg-[var(--bg-card)] shadow-lg py-1 text-sm"
        :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      >
        <button
          class="w-full text-left px-3 py-2 hover:bg-[var(--bg-muted)] transition"
          @click="handleMenuRename"
        >
          重命名
        </button>
        <button
          class="w-full text-left px-3 py-2 text-red-600 hover:bg-[var(--bg-muted)] transition"
          @click="handleMenuDelete"
        >
          删除
        </button>
      </div>
    </Teleport>
  </aside>
</template>

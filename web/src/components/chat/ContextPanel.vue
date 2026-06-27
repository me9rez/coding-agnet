<script setup lang="ts">
import { CheckCircle2, Clock, FolderOpen, History, Lightbulb } from '@lucide/vue'
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useWorkspaceStore } from '@/stores/workspace'

const chatStore = useChatStore()
const workspaceStore = useWorkspaceStore()

const recentOps = computed(() => {
  return chatStore.messages
    .filter((m) => m.role === 'tool' && (m.toolCall?.name || m.toolExecution?.name))
    .slice(-5)
    .map((m) => ({
      name: m.toolCall?.name || m.toolExecution?.name || '',
      ok: m.toolExecution?.finished === true ? m.toolExecution.ok : undefined,
    }))
})
</script>

<template>
  <aside class="h-full w-72 flex-shrink-0 border-l border-[var(--border)] bg-[var(--bg-page)] flex flex-col">
    <div class="h-14 flex items-center px-5 border-b border-[var(--border)]">
      <span class="text-sm font-medium">进度</span>
    </div>

    <div class="flex-1 overflow-y-auto py-4 px-4 space-y-5">
      <div class="rounded-xl bg-[var(--bg-card)] border border-[var(--border)] p-4 shadow-[var(--shadow)]">
        <div class="flex items-center gap-2 text-[var(--text-muted)] text-xs mb-3">
          <Clock class="w-3.5 h-3.5" />
          <span>任务执行进度</span>
        </div>
        <p class="text-sm text-[var(--text-muted)]">
          任务执行进度将显示在这里
        </p>
      </div>

      <div>
        <div class="flex items-center justify-between px-1 mb-2">
          <span class="text-xs font-medium text-[var(--text-muted)]">工作区</span>
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-muted)] text-[var(--text-subtle)]">
            {{ workspaceStore.workspace?.name || '-' }}
          </span>
        </div>
        <div class="rounded-xl bg-[var(--bg-card)] border border-[var(--border)] p-3 shadow-[var(--shadow)] flex items-center gap-2">
          <FolderOpen class="w-4 h-4 text-[var(--text-subtle)]" />
          <div class="min-w-0">
            <div class="text-sm truncate">
              {{ workspaceStore.workspace?.name || '未获取到工作区' }}
            </div>
            <div class="text-xs text-[var(--text-subtle)] truncate">
              {{ workspaceStore.workspace?.path || '' }}
            </div>
          </div>
        </div>
      </div>

      <div>
        <div class="px-1 mb-2 text-xs font-medium text-[var(--text-muted)]">
          项目指令 · 点击添加
        </div>
        <div class="rounded-xl bg-[var(--bg-card)] border border-[var(--border)] p-3 shadow-[var(--shadow)] text-sm text-[var(--text-muted)]">
          暂无项目指令
        </div>
      </div>

      <div>
        <div class="px-1 mb-2 text-xs font-medium text-[var(--text-muted)]">
          项目记忆
        </div>
        <div class="rounded-xl bg-[var(--bg-card)] border border-[var(--border)] p-3 shadow-[var(--shadow)] text-sm text-[var(--text-muted)] flex items-center gap-2">
          <Lightbulb class="w-4 h-4" />
          暂无项目记忆
        </div>
      </div>

      <div>
        <div class="px-1 mb-2 text-xs font-medium text-[var(--text-muted)] flex items-center gap-1">
          <History class="w-3.5 h-3.5" />
          <span>操作记录 {{ recentOps.length }} ops</span>
        </div>
        <ul v-if="recentOps.length" class="space-y-1.5">
          <li
            v-for="(op, idx) in recentOps"
            :key="idx"
            class="flex items-center gap-2 text-sm px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border)]"
          >
            <CheckCircle2 v-if="op.ok === true" class="w-4 h-4 text-green-600" />
            <CheckCircle2 v-else-if="op.ok === false" class="w-4 h-4 text-red-600" />
            <span v-else class="w-4 h-4 rounded-full border-2 border-[var(--text-subtle)]" />
            <span class="truncate">{{ op.name }}</span>
          </li>
        </ul>
        <div v-else class="text-sm text-[var(--text-muted)] px-1">
          暂无操作记录
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  ArrowLeft,
  BarChart3,
  Bot,
  Brain,
  Flag,
  Heart,
  Info,
  LayoutGrid,
  Monitor,
  Shield,
  SlidersHorizontal,
  Sparkles,
} from '@lucide/vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()

const menuItems = [
  { name: 'settings-usage', label: '用量', icon: BarChart3, to: '/settings/usage' },
  { name: 'settings-models', label: '模型', icon: Bot, to: '/settings/models' },
  { name: 'settings-channels', label: '频道', icon: LayoutGrid, to: '/settings/channels' },
  { name: 'settings-memory', label: '记忆', icon: Brain, to: '/settings/memory' },
  { name: 'settings-personality', label: '性格', icon: Heart, to: '/settings/personality' },
  { name: 'settings-security', label: '安全', icon: Shield, to: '/settings/security' },
  { name: 'settings-preferences', label: '偏好', icon: SlidersHorizontal, to: '/settings/preferences' },
  { name: 'settings-diagnostics', label: '诊断', icon: Monitor, to: '/settings/diagnostics' },
  { name: 'settings-feedback', label: '反馈', icon: Flag, to: '/settings/feedback' },
  { name: 'settings-version', label: '版本', icon: Info, to: '/settings/version' },
]

function goBack() {
  router.push('/')
}
</script>

<template>
  <div class="h-full flex flex-col bg-[var(--bg-page)] text-[var(--text)]">
    <header class="h-14 flex items-center px-5 border-b border-[var(--border)] bg-[var(--bg-page)] flex-shrink-0">
      <button
        class="flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] transition"
        @click="goBack"
      >
        <ArrowLeft class="w-4 h-4" />
        <span>系统设置</span>
      </button>
    </header>

    <div class="flex-1 flex min-h-0">
      <aside class="w-60 flex-shrink-0 border-r border-[var(--border)] bg-[var(--bg-page)] overflow-y-auto">
        <nav class="p-3 space-y-1">
          <RouterLink
            v-for="item in menuItems"
            :key="item.name"
            :to="item.to"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition"
            :class="{
              'bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)] text-[var(--text)] font-medium': route.name === item.name,
              'text-[var(--text-muted)] hover:bg-[var(--bg-muted)]': route.name !== item.name,
            }"
          >
            <component :is="item.icon" class="w-4 h-4" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
      </aside>

      <main class="flex-1 overflow-y-auto bg-[var(--bg-page)]">
        <RouterView />
      </main>
    </div>
  </div>
</template>

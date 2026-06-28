<script setup lang="ts">
import { Plug, Wrench } from '@lucide/vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/toolbox/skills', label: '技能', icon: Wrench },
  { path: '/toolbox/connectors', label: '连接器', icon: Plug },
]
</script>

<template>
  <div class="h-full flex">
    <aside class="w-48 bg-[var(--bg-page)] border-r border-[var(--border)] flex flex-col">
      <div class="p-4 border-b border-[var(--border)]">
        <RouterLink to="/" class="flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] transition">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <span>工具箱</span>
        </RouterLink>
      </div>
      <nav class="p-2 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition"
          :class="
            route.path.startsWith(item.path)
              ? 'bg-[var(--bg-card)] text-[var(--text)] font-medium border border-[var(--border)] shadow-[var(--shadow)]'
              : 'text-[var(--text-muted)] hover:bg-[var(--bg-muted)]'
          "
        >
          <component :is="item.icon" class="w-4 h-4" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>
    <main class="flex-1 overflow-hidden">
      <RouterView />
    </main>
  </div>
</template>

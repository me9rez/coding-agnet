<script setup lang="ts">
import { AlertCircle, ChevronDown, Globe, ImagePlus, Plus } from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import type { ProviderConfig } from '@/types/session'

const settingsStore = useSettingsStore()
const showClearConfirm = ref(false)

const enabledCount = computed(() => {
  return Object.values(settingsStore.settings.providers).filter((p) => (p as ProviderConfig).enabled !== false).length
})

function providerEntries() {
  return Object.entries(settingsStore.settings.providers).map(([id, config]) => ({
    id,
    config: config as ProviderConfig,
  }))
}

function providerLabel(id: string): string {
  const labels: Record<string, string> = {
    deepseek: '深度求索 (DeepSeek)',
    openrouter: 'OpenRouter',
    apifree: 'apifree',
  }
  return labels[id] || id
}

function providerDescription(id: string, config: ProviderConfig): string {
  return config.models.map((m) => m.id).join(', ')
}

function toggleProvider(id: string) {
  const config = settingsStore.settings.providers[id]
  if (!config) return
  settingsStore.updateProvider(id, { enabled: config.enabled === false })
}

async function handleSave() {
  await settingsStore.saveSettings()
}

function clearAllKeys() {
  const next = { ...settingsStore.settings.providers }
  for (const id of Object.keys(next)) {
    const existing = next[id] ?? { models: [] }
    next[id] = { ...existing, apiKey: '' }
  }
  settingsStore.updateSettings({ providers: next })
  settingsStore.saveSettings()
  showClearConfirm.value = false
}

onMounted(() => {
  settingsStore.loadSettings()
})

watch(
  () => settingsStore.settings.primaryModel,
  async (value, oldValue) => {
    if (value && value !== oldValue) {
      await settingsStore.saveSettings()
    }
  },
)
</script>

<template>
  <div class="p-8 max-w-4xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-xl font-semibold">
          模型
        </h1>
        <p class="text-sm text-[var(--text-muted)] mt-1">
          {{ enabledCount }} 个已启用
        </p>
      </div>
      <button
        class="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-[var(--border)] text-sm hover:bg-[var(--bg-muted)] transition"
      >
        <Plus class="w-4 h-4" />
        <span>添加 AI 服务</span>
      </button>
    </div>

    <div v-if="settingsStore.loading" class="py-12 text-center text-sm text-[var(--text-muted)]">
      加载中…
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="{ id, config } in providerEntries()"
        :key="id"
        class="rounded-2xl border p-5 transition"
        :class="config.enabled !== false
          ? 'bg-[var(--bg-card)] border-[var(--border)] shadow-[var(--shadow)]'
          : 'bg-[var(--bg-page)] border-transparent opacity-70'"
      >
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-medium">
              {{ providerLabel(id) }}
            </h3>
            <p class="text-sm text-[var(--text-muted)] mt-1">
              {{ providerDescription(id, config) }}
            </p>
          </div>
          <button
            class="relative w-11 h-6 rounded-full transition"
            :class="config.enabled !== false ? 'bg-[#d9896d]' : 'bg-[var(--bg-muted)]'"
            @click="toggleProvider(id)"
          >
            <span
              class="absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform"
              :class="config.enabled !== false ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
        </div>
      </div>

      <div class="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow)]">
        <h3 class="font-medium mb-4">
          默认模型
        </h3>
        <div class="relative mb-4">
          <select
            v-model="settingsStore.settings.primaryModel"
            class="w-full appearance-none px-3 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] text-sm"
          >
            <option v-for="opt in settingsStore.modelOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)] pointer-events-none" />
        </div>

        <div>
          <label class="block text-sm font-medium mb-2">Max Turns</label>
          <input
            v-model.number="settingsStore.settings.max_turns"
            type="number"
            class="w-full px-3 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] text-sm"
            @change="handleSave"
          >
        </div>
      </div>

      <div class="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-[var(--shadow)] overflow-hidden">
        <div class="px-5 py-3 bg-[var(--bg-muted)] text-sm font-medium">
          辅助能力
        </div>
        <div class="px-5 py-4 flex items-center justify-between border-b border-[var(--border)]">
          <div class="flex items-center gap-3">
            <AlertCircle class="w-4 h-4 text-amber-500" />
            <Globe class="w-4 h-4 text-[var(--text-muted)]" />
            <span class="text-sm">联网搜索</span>
          </div>
          <button class="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-lg">
            <span>需自定义配置</span>
            <ChevronDown class="w-3 h-3" />
          </button>
        </div>
        <div class="px-5 py-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <AlertCircle class="w-4 h-4 text-amber-500" />
            <ImagePlus class="w-4 h-4 text-[var(--text-muted)]" />
            <span class="text-sm">图片生成</span>
          </div>
          <button class="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-lg">
            <span>需自定义配置</span>
            <ChevronDown class="w-3 h-3" />
          </button>
        </div>
      </div>

      <div class="flex justify-end pt-4">
        <button
          class="flex items-center gap-2 text-sm text-red-600 hover:text-red-700 transition"
          @click="showClearConfirm = true"
        >
          <span class="i-carbon-trash-can w-4 h-4" />
          <span>清除所有已保存密钥</span>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="showClearConfirm"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="showClearConfirm = false"
      >
        <div class="w-full max-w-sm rounded-2xl bg-[var(--bg-card)] p-6 shadow-xl">
          <h3 class="font-semibold mb-2">
            清除所有已保存密钥
          </h3>
          <p class="text-sm text-[var(--text-muted)] mb-6">
            此操作会清空所有 AI 服务的 API key，且无法撤销。是否继续？
          </p>
          <div class="flex justify-end gap-3">
            <button
              class="px-4 py-2 rounded-xl text-sm border border-[var(--border)] hover:bg-[var(--bg-muted)] transition"
              @click="showClearConfirm = false"
            >
              取消
            </button>
            <button
              class="px-4 py-2 rounded-xl text-sm bg-red-600 text-white hover:bg-red-700 transition"
              @click="clearAllKeys"
            >
              确认清除
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

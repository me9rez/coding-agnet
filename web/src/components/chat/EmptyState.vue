<script setup lang="ts">
import {
  Briefcase,
  ChevronDown,
  Clock,
  Database,
  FileText,
  Folder,
  Globe,
  Plus,
  Send,
} from '@lucide/vue'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { gatewayService } from '@/services/gateway'
import { useSessionsStore } from '@/stores/sessions'
import type { ProviderConfig, Settings } from '@/types/session'

const emit = defineEmits<{
  send: [text: string, model: string]
  useSuggestion: [text: string, model: string]
}>()

const sessionsStore = useSessionsStore()
const text = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const settings = ref<Settings | null>(null)
let unsubscribeOpen: (() => void) | null = null

const modelOptions = computed(() => {
  const opts: { value: string; label: string }[] = []
  if (!settings.value) return opts
  for (const [providerId, provider] of Object.entries(settings.value.providers)) {
    for (const model of (provider as ProviderConfig).models) {
      opts.push({
        value: `${providerId}/${model.id}`,
        label: `${providerId} / ${model.name || model.id}`,
      })
    }
  }
  return opts
})

const categories = [
  { key: 'office', label: '办公整理', icon: Briefcase },
  { key: 'data', label: '数据处理', icon: Database },
  { key: 'content', label: '内容创作', icon: FileText },
  { key: 'web', label: '网页生成', icon: Globe },
  { key: 'scheduled', label: '定时任务', icon: Clock, active: true },
]

const suggestions = [
  '每天早上 8 点推送今日科技资讯摘要',
  '每天早上抓取天气预报并推送给我',
  '每隔 2 小时提醒我喝水和休息',
  '每周一早上推送本周热门电影和书籍推荐',
  '整理桌面文件，按类型分到不同文件夹',
  '帮我分析这份销售数据并生成图表',
  '写一份本周项目进展周报',
  '生成一个个人介绍网页',
]

async function loadSettings() {
  if (!gatewayService.isConnected()) return
  try {
    const data = await gatewayService.call<Settings>('getSettings')
    settings.value = data
  } catch (err) {
    console.error('Failed to load settings', err)
  }
}

const effectiveModel = computed(() => settings.value?.primaryModel || '')

async function handleModelChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (!value || !settings.value) return
  try {
    await gatewayService.call<Settings>('updateSettings', { primaryModel: value })
    settings.value.primaryModel = value
  } catch (err) {
    console.error('Failed to update model', err)
  }
}

function adjustHeight() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight}px`
}

function handleSend() {
  const value = text.value.trim()
  if (!value) return
  emit('send', value, effectiveModel.value)
  text.value = ''
  nextTick(adjustHeight)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function fillCategory(label: string) {
  text.value = `帮我${label}：` + (text.value ? `\n${text.value}` : '')
  nextTick(adjustHeight)
  textareaRef.value?.focus()
}

function useSuggestion(suggestion: string) {
  emit('useSuggestion', suggestion, effectiveModel.value)
}

async function handleNewChat() {
  await sessionsStore.createSession('新对话')
}

onMounted(() => {
  unsubscribeOpen = gatewayService.on('open', () => {
    loadSettings()
  })
  loadSettings()
})

onUnmounted(() => {
  unsubscribeOpen?.()
})
</script>

<template>
  <div class="flex-1 flex flex-col items-center justify-center px-6 py-8 overflow-y-auto">
    <div class="w-20 h-20 rounded-full bg-[var(--bg-muted)] flex items-center justify-center text-4xl mb-5 shadow-[var(--shadow)]">
      🤖
    </div>

    <h2 class="text-2xl font-semibold mb-2 flex items-center gap-2">
      <span>交给 Coding Agent 就行啦</span>
      <span class="text-2xl">✨</span>
    </h2>
    <p class="text-sm text-[var(--text-muted)] mb-8">
      嘿～我是你的桌面小伙伴！从今天起啥都交给我吧～
    </p>

    <div class="w-full max-w-2xl mb-5">
      <div class="rounded-3xl bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)] px-4 py-4">
        <textarea
          ref="textareaRef"
          v-model="text"
          rows="1"
          placeholder="描述你想定时执行的任务..."
          class="w-full resize-none bg-transparent outline-none text-base max-h-40 mb-3"
          @keydown="handleKeydown"
          @input="adjustHeight"
        />

        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <button class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition">
              <Folder class="w-4 h-4" />
              <span>添加工作区</span>
              <ChevronDown class="w-3.5 h-3.5" />
            </button>
            <button class="p-1.5 rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition">
              <Plus class="w-4 h-4" />
            </button>
          </div>

          <div class="flex items-center gap-2">
            <div v-if="settings" class="relative">
              <select
                :value="effectiveModel"
                class="appearance-none pl-3 pr-7 py-1.5 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-page)] text-[var(--text-muted)] outline-none focus:border-[var(--text-subtle)]"
                @change="handleModelChange"
              >
                <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[var(--text-subtle)] pointer-events-none" />
            </div>
            <button
              class="p-2.5 rounded-xl bg-[var(--text)] text-[var(--bg-card)] hover:opacity-90 transition disabled:opacity-40"
              :disabled="!text.trim()"
              @click="handleSend"
            >
              <Send class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-center justify-center gap-2 mb-8 max-w-2xl">
      <button
        v-for="cat in categories"
        :key="cat.key"
        class="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm border transition"
        :class="cat.active
          ? 'bg-[var(--text)] text-[var(--bg-card)] border-[var(--text)]'
          : 'bg-[var(--bg-card)] border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--text-subtle)] hover:text-[var(--text)]'"
        @click="fillCategory(cat.label)"
      >
        <component :is="cat.icon" class="w-4 h-4" />
        <span>{{ cat.label }}</span>
      </button>
    </div>

    <div class="w-full max-w-2xl">
      <div class="flex items-center gap-4 mb-4">
        <div class="flex-1 h-px bg-[var(--border)]" />
        <span class="text-xs text-[var(--text-subtle)]">试试这样说</span>
        <div class="flex-1 h-px bg-[var(--border)]" />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          v-for="(s, idx) in suggestions"
          :key="idx"
          class="text-left px-4 py-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)] text-sm text-[var(--text-muted)] hover:border-[var(--text-subtle)] hover:text-[var(--text)] transition shadow-[var(--shadow)]"
          @click="useSuggestion(s)"
        >
          {{ s }}
        </button>
      </div>
    </div>
  </div>
</template>

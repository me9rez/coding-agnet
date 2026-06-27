<script setup lang="ts">
import { ChevronDown, Plus, Send, Square } from '@lucide/vue'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { gatewayService } from '@/services/gateway'
import { useChatStore } from '@/stores/chat'
import type { ProviderConfig, Settings } from '@/types/session'

const props = defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  stop: []
}>()

const chatStore = useChatStore()
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

const estimatedTokens = computed(() => {
  let chars = 0
  for (const m of chatStore.messages) {
    chars += m.content.length
    if (m.thinking) chars += m.thinking.length
    if (m.toolExecution) chars += m.toolExecution.output.length
  }
  return Math.round(chars / 4)
})

async function loadSettings() {
  if (!gatewayService.isConnected()) return
  try {
    const data = await gatewayService.call<Settings>('getSettings')
    settings.value = data
  } catch (err) {
    console.error('Failed to load settings', err)
  }
}

async function handleModelChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (!value) return
  try {
    await gatewayService.call<Settings>('updateSettings', { selectedModel: value })
    if (settings.value) {
      settings.value.selectedModel = value
    }
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
  if (!value || props.disabled) return
  emit('send', value)
  text.value = ''
  nextTick(adjustHeight)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function handleInput() {
  adjustHeight()
}

function handleStop() {
  emit('stop')
}

function setText(value: string) {
  text.value = value
  nextTick(adjustHeight)
  nextTick(() => textareaRef.value?.focus())
}

defineExpose({ setText })

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
  <div class="px-8 py-4 border-t border-[var(--border)] bg-[var(--bg-page)]">
    <div class="max-w-3xl mx-auto">
      <div class="relative flex items-end gap-2 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)] px-4 py-3">
        <button class="p-1.5 rounded-lg text-[var(--text-subtle)] hover:bg-[var(--bg-muted)] transition flex-shrink-0">
          <Plus class="w-5 h-5" />
        </button>

        <textarea
          ref="textareaRef"
          v-model="text"
          rows="1"
          :disabled="disabled"
          placeholder="想让 Coding Agent 帮你做点什么？"
          class="flex-1 resize-none bg-transparent outline-none text-sm max-h-40 py-1.5"
          @keydown="handleKeydown"
          @input="handleInput"
        />

        <button
          v-if="disabled"
          class="p-2 rounded-xl bg-[var(--bg-muted)] text-[var(--text)] hover:bg-[var(--border)] transition flex-shrink-0"
          title="停止"
          @click="handleStop"
        >
          <Square class="w-4 h-4" />
        </button>
        <button
          v-else
          class="p-2 rounded-xl bg-[var(--text)] text-[var(--bg-card)] hover:opacity-90 transition disabled:opacity-40 flex-shrink-0"
          :disabled="!text.trim()"
          @click="handleSend"
        >
          <Send class="w-4 h-4" />
        </button>
      </div>

      <div class="flex items-center justify-between mt-2 px-1">
        <div v-if="settings" class="relative">
          <select
            :value="settings.selectedModel"
            class="appearance-none pl-2 pr-6 py-1 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-muted)] outline-none focus:border-[var(--text-subtle)]"
            @change="handleModelChange"
          >
            <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[var(--text-subtle)] pointer-events-none" />
        </div>
        <div v-else />

        <div class="text-xs text-[var(--text-subtle)]">
          上下文水位 · 本地估算 {{ estimatedTokens.toLocaleString() }} tokens
        </div>
      </div>
    </div>
  </div>
</template>

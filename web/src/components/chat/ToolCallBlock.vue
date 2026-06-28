<script setup lang="ts">
import { CheckCircle2, ChevronDown, ChevronRight, Terminal, XCircle } from '@lucide/vue'
import { computed, ref } from 'vue'
import type { UiMessage } from '@/types/session'

const props = defineProps<{
  message: UiMessage
}>()

const status = computed(() => {
  if (!props.message.toolExecution || props.message.toolExecution.finished === false) return 'pending'
  return props.message.toolExecution.ok ? 'success' : 'error'
})

const expanded = ref(status.value === 'pending')
const showParams = ref(true)
const showResult = ref(true)

const toolName = computed(() => props.message.toolCall?.name || 'tool')

const params = computed(() => {
  try {
    const args = JSON.parse(props.message.toolCall?.arguments || '{}')
    return args
  } catch {
    return {}
  }
})

const paramsStr = computed(() => {
  const p = params.value
  if (Object.keys(p).length === 0) return ''
  return JSON.stringify(p, null, 2)
})

const output = computed(() => props.message.toolExecution?.output || '')
</script>

<template>
  <div class="w-full max-w-full rounded-xl bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)] overflow-hidden">
    <button
      class="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-[var(--bg-muted)] transition"
      @click="expanded = !expanded"
    >
      <span class="flex items-center gap-1.5 text-sm font-medium text-[var(--text)]">
        <Terminal class="w-3.5 h-3.5 text-[var(--text-subtle)]" />
        执行 {{ toolName }}
      </span>
      <span class="flex-1 min-w-0" />
      <span
        class="flex items-center gap-1 text-xs flex-shrink-0"
        :class="status === 'success' ? 'text-green-600' : status === 'error' ? 'text-red-600' : 'text-[var(--text-muted)]'"
      >
        <CheckCircle2 v-if="status === 'success'" class="w-3.5 h-3.5" />
        <XCircle v-else-if="status === 'error'" class="w-3.5 h-3.5" />
        <span v-else class="w-3.5 h-3.5 rounded-full border-2 border-current animate-spin" />
        {{ status === 'success' ? '成功' : status === 'error' ? '失败' : '执行中' }}
      </span>
      <ChevronDown
        class="w-4 h-4 text-[var(--text-subtle)] flex-shrink-0 transition-transform"
        :class="expanded ? 'rotate-180' : ''"
      />
    </button>

    <div v-if="expanded" class="px-3 pb-3 pt-1">
      <div class="flex items-center gap-2 mb-2">
        <button
          class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border border-[var(--border)] bg-[var(--bg-muted)] text-[var(--text-muted)] hover:bg-[var(--bg-page)] transition"
          @click.stop="showParams = !showParams"
        >
          参数
          <ChevronDown v-if="showParams" class="w-3 h-3" />
          <ChevronRight v-else class="w-3 h-3" />
        </button>
        <button
          class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border border-[var(--border)] bg-[var(--bg-muted)] text-[var(--text-muted)] hover:bg-[var(--bg-page)] transition"
          @click.stop="showResult = !showResult"
        >
          结果
          <ChevronDown v-if="showResult" class="w-3 h-3" />
          <ChevronRight v-else class="w-3 h-3" />
        </button>
      </div>

      <div v-if="showParams" class="mb-2">
        <div class="text-xs text-[var(--text-subtle)] mb-1">输入</div>
        <pre v-if="paramsStr" class="text-xs bg-[var(--bg-muted)] rounded-lg p-2.5 overflow-x-auto whitespace-pre-wrap break-all max-h-40 overflow-y-auto">{{ paramsStr }}</pre>
        <div v-else class="text-xs text-[var(--text-subtle)]">无参数</div>
      </div>

      <div v-if="showResult">
        <div class="text-xs text-[var(--text-subtle)] mb-1">输出</div>
        <pre class="text-xs bg-[var(--bg-muted)] rounded-lg p-2.5 overflow-x-auto whitespace-pre-wrap break-all max-h-60 overflow-y-auto min-h-[2rem]">{{ output || '等待输出…' }}</pre>
      </div>
    </div>
  </div>
</template>

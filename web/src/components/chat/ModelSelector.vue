<script setup lang="ts">
import { Check, ChevronDown, Clock, Search } from '@lucide/vue'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'

interface ModelOption {
  value: string
  label: string
  providerId: string
  providerName: string
  modelId: string
}

const props = withDefaults(defineProps<{
  options: ModelOption[]
  value: string
  placement?: 'bottom' | 'top'
}>(), {
  placement: 'bottom',
})

const emit = defineEmits<{
  change: [value: string]
}>()

const open = ref(false)
const search = ref('')
const dropdownRef = ref<HTMLDivElement | null>(null)
const searchRef = ref<HTMLInputElement | null>(null)
const pos = ref({ left: 0, top: 0, bottom: 0, placeAbove: false })

const recentKey = 'model-selector-recent'

function getRecent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(recentKey) || '[]')
  } catch {
    return []
  }
}

function addRecent(value: string) {
  const recent = getRecent().filter((v) => v !== value)
  recent.unshift(value)
  localStorage.setItem(recentKey, JSON.stringify(recent.slice(0, 5)))
}

const recentModels = computed(() => {
  const recent = getRecent()
  return recent
    .map((v) => props.options.find((o) => o.value === v))
    .filter(Boolean) as ModelOption[]
})

const selectedModel = computed(() => props.options.find((o) => o.value === props.value))

const groupedModels = computed(() => {
  const q = search.value.toLowerCase()
  const groups: Record<string, ModelOption[]> = {}
  for (const opt of props.options) {
    if (q && !opt.modelId.toLowerCase().includes(q) && !opt.providerName.toLowerCase().includes(q) && !opt.label.toLowerCase().includes(q)) {
      continue
    }
    const key = opt.providerId
    if (!groups[key]) groups[key] = []
    groups[key].push(opt)
  }
  return groups
})

const providerLabels: Record<string, string> = {
  deepseek: '深度求索 (DEEPSEEK)',
  openrouter: 'OpenRouter',
  apifree: 'apifree',
}

function providerLabel(id: string): string {
  return providerLabels[id] || id
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    const btn = dropdownRef.value?.querySelector('button')
    if (btn) {
      const rect = btn.getBoundingClientRect()
      const spaceBelow = window.innerHeight - rect.bottom
      const placeAbove = props.placement === 'top' || spaceBelow < 300
      pos.value = {
        left: rect.left,
        top: rect.bottom + 4,
        bottom: window.innerHeight - rect.top + 4,
        placeAbove,
      }
    }
    search.value = ''
    nextTick(() => searchRef.value?.focus())
  }
}

function select(value: string) {
  addRecent(value)
  emit('change', value)
  open.value = false
  search.value = ''
}

function handleClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    open.value = false
    search.value = ''
  }
}

onMounted(() => document.addEventListener('mousedown', handleClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', handleClickOutside))
</script>

<template>
  <div ref="dropdownRef" class="relative">
    <button
      class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-xl border border-[var(--border)] bg-[var(--bg-page)] text-[var(--text-muted)] outline-none hover:border-[var(--text-subtle)] transition"
      @click="toggle"
    >
      <span class="max-w-[160px] truncate">{{ selectedModel?.modelId || '选择模型' }}</span>
      <ChevronDown class="w-3 h-3 flex-shrink-0" :class="open ? 'rotate-180' : ''" />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        class="fixed z-50 w-72 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] shadow-xl overflow-hidden"
        :style="pos.placeAbove
          ? { left: pos.left + 'px', bottom: pos.bottom + 'px' }
          : { left: pos.left + 'px', top: pos.top + 'px' }"
      >
        <!-- Search -->
        <div class="p-2 border-b border-[var(--border)]">
          <div class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-[var(--bg-page)]">
            <Search class="w-3.5 h-3.5 text-[var(--text-subtle)]" />
            <input
              ref="searchRef"
              v-model="search"
              type="text"
              placeholder="搜索..."
              class="flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--text-subtle)]"
            >
          </div>
        </div>

        <div class="max-h-64 overflow-y-auto py-1">
          <!-- Recent -->
          <template v-if="!search && recentModels.length">
            <div class="px-3 py-1.5 text-[10px] font-medium text-[var(--text-subtle)] uppercase tracking-wider flex items-center gap-1.5">
              <Clock class="w-3 h-3" />
              <span>RECENT</span>
            </div>
            <button
              v-for="opt in recentModels"
              :key="'r-' + opt.value"
              class="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-[var(--bg-muted)] transition"
              @click="select(opt.value)"
            >
              <span>{{ opt.modelId }}</span>
              <Check v-if="opt.value === value" class="w-4 h-4 text-[#d9896d]" />
            </button>
            <div class="mx-3 my-1 h-px bg-[var(--border)]" />
          </template>

          <!-- Grouped by provider -->
          <template v-for="(models, providerId) in groupedModels" :key="providerId">
            <div class="px-3 py-1.5 text-[10px] font-medium text-[var(--text-subtle)] uppercase tracking-wider">
              {{ providerLabel(providerId as string) }}
            </div>
            <button
              v-for="opt in models"
              :key="opt.value"
              class="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-[var(--bg-muted)] transition"
              @click="select(opt.value)"
            >
              <span>{{ opt.modelId }}</span>
              <Check v-if="opt.value === value" class="w-4 h-4 text-[#d9896d]" />
            </button>
          </template>

          <div v-if="Object.keys(groupedModels).length === 0" class="px-3 py-6 text-center text-sm text-[var(--text-subtle)]">
            无匹配模型
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

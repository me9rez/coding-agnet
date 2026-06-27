<script setup lang="ts">
import { ChevronDown } from '@lucide/vue'
import { ref, watch } from 'vue'
import { gatewayService } from '@/services/gateway'
import type { ProviderConfig, Settings } from '@/types/session'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const defaultSettings: Settings = {
  selectedModel: 'deepseek/deepseek-v4-flash',
  providers: {
    deepseek: {
      api: 'openai-completions',
      baseUrl: 'https://api.deepseek.com/v1',
      apiKey: '',
      models: [
        {
          id: 'deepseek-v4-flash',
          name: 'DeepSeek V4 Flash',
          contextWindow: 128000,
          maxTokens: 8000,
          reasoning: true,
          thinking_level: ['high', 'max'],
          input: ['text'],
        },
        {
          id: 'deepseek-v4',
          name: 'DeepSeek V4',
          contextWindow: 128000,
          maxTokens: 8000,
          reasoning: true,
          thinking_level: ['high', 'max'],
          input: ['text'],
        },
      ],
    },
  },
  max_turns: 25,
}

const settings = ref<Settings>({ ...defaultSettings })
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

async function loadSettings() {
  loading.value = true
  error.value = null
  try {
    const data = await gatewayService.call<Settings>('getSettings')
    settings.value = { ...defaultSettings, ...data }
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  error.value = null
  try {
    await gatewayService.call<Settings>('updateSettings', { ...settings.value })
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}

function modelOptions() {
  const options: { value: string; label: string }[] = []
  for (const [providerId, provider] of Object.entries(settings.value.providers)) {
    for (const model of (provider as ProviderConfig).models) {
      options.push({
        value: `${providerId}/${model.id}`,
        label: `${providerId} / ${model.name || model.id}`,
      })
    }
  }
  return options
}

watch(
  () => props.modelValue,
  (open, wasOpen) => {
    if (open && !wasOpen) loadSettings()
  },
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="close"
    >
      <div class="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl bg-white dark:bg-neutral-900 shadow-xl p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">
            设置
          </h2>
          <button
            class="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800"
            @click="close"
          >
            <span class="i-carbon-close" />
          </button>
        </div>

        <div v-if="loading" class="py-8 text-center text-sm text-neutral-500">
          加载中…
        </div>

        <form v-else class="space-y-4" @submit.prevent="saveSettings">
          <div>
            <label class="block text-sm font-medium mb-1">默认模型</label>
            <div class="relative">
              <select
                v-model="settings.selectedModel"
                class="w-full appearance-none px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 outline-none focus:border-neutral-500"
              >
                <option v-for="opt in modelOptions()" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500 pointer-events-none" />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">Max Turns</label>
            <input
              v-model.number="settings.max_turns"
              type="number"
              class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 outline-none focus:border-neutral-500"
            >
          </div>

          <div v-if="error" class="text-sm text-red-600 dark:text-red-400">
            {{ error }}
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
              @click="close"
            >
              取消
            </button>
            <button
              type="submit"
              class="px-4 py-2 rounded-lg bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 hover:opacity-90 transition disabled:opacity-50"
              :disabled="saving"
            >
              {{ saving ? '保存中…' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

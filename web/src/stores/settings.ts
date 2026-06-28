import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { gatewayService } from '@/services/gateway'
import type { ProviderConfig, Settings } from '@/types/session'

const defaultSettings: Settings = {
  primaryModel: 'deepseek/deepseek-v4-flash',
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

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Settings>({ ...defaultSettings })
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  const modelOptions = computed(() => {
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
  })

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

  async function saveSettings(partial?: Partial<Settings>) {
    saving.value = true
    error.value = null
    try {
      const next = { ...settings.value, ...partial }
      const data = await gatewayService.call<Settings>('updateSettings', next)
      settings.value = { ...defaultSettings, ...data }
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    } finally {
      saving.value = false
    }
  }

  function updateSettings(partial: Partial<Settings>) {
    settings.value = { ...settings.value, ...partial }
  }

  function updateProvider(providerId: string, patch: Partial<ProviderConfig>) {
    const next = { ...settings.value }
    next.providers = { ...next.providers }
    const existing = next.providers[providerId] ?? { models: [] }
    next.providers[providerId] = { ...existing, ...patch, models: patch.models ?? existing.models }
    settings.value = next
  }

  return {
    settings,
    loading,
    saving,
    error,
    modelOptions,
    loadSettings,
    saveSettings,
    updateSettings,
    updateProvider,
  }
})

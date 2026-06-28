import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { gatewayService } from '@/services/gateway'

export interface Connector {
  name: string
  description: string
  installed: boolean
  type: 'builtin' | 'custom'
}

export interface ConnectorConfig {
  type: 'stdio' | 'streamable-http'
  command?: string
  args?: string[]
  url?: string
  env?: Record<string, string>
  description?: string
}

export interface ConnectorDetail extends Connector {
  config: ConnectorConfig
}

export const useConnectorsStore = defineStore('connectors', () => {
  const connectors = ref<Connector[]>([])
  const selectedConnector = ref<ConnectorDetail | null>(null)
  const loading = ref(false)
  const searchQuery = ref('')

  const builtinConnectors = computed(() =>
    connectors.value
      .filter((c) => c.type === 'builtin')
      .sort((a, b) => a.name.localeCompare(b.name)),
  )

  const customConnectors = computed(() =>
    connectors.value
      .filter((c) => c.type === 'custom')
      .sort((a, b) => a.name.localeCompare(b.name)),
  )

  const filteredBuiltinConnectors = computed(() => {
    if (!searchQuery.value) return builtinConnectors.value
    const q = searchQuery.value.toLowerCase()
    return builtinConnectors.value.filter(
      (c) => c.name.toLowerCase().includes(q) || c.description.toLowerCase().includes(q),
    )
  })

  const filteredCustomConnectors = computed(() => {
    if (!searchQuery.value) return customConnectors.value
    const q = searchQuery.value.toLowerCase()
    return customConnectors.value.filter(
      (c) => c.name.toLowerCase().includes(q) || c.description.toLowerCase().includes(q),
    )
  })

  async function fetchConnectors() {
    loading.value = true
    try {
      const data = await gatewayService.call<{ connectors: Connector[] }>('listConnectors')
      connectors.value = data.connectors || []
    } catch (err) {
      console.error('Failed to fetch connectors:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchConnectorDetail(name: string) {
    try {
      const data = await gatewayService.call<ConnectorDetail>('getConnector', { name })
      selectedConnector.value = data
      return data
    } catch (err) {
      console.error('Failed to fetch connector detail:', err)
      return null
    }
  }

  async function installConnector(name: string, config?: ConnectorConfig) {
    try {
      const data = await gatewayService.call<{ success: boolean }>('installConnector', { name, config })
      if (data.success) {
        await fetchConnectors()
      }
      return data.success
    } catch (err) {
      console.error('Failed to install connector:', err)
      return false
    }
  }

  async function uninstallConnector(name: string) {
    try {
      const data = await gatewayService.call<{ success: boolean }>('uninstallConnector', { name })
      if (data.success) {
        if (selectedConnector.value?.name === name) {
          selectedConnector.value = null
        }
        await fetchConnectors()
      }
      return data.success
    } catch (err) {
      console.error('Failed to uninstall connector:', err)
      return false
    }
  }

  async function updateConnector(name: string, config: ConnectorConfig) {
    try {
      const data = await gatewayService.call<{ success: boolean }>('updateConnector', { name, config })
      if (data.success) {
        if (selectedConnector.value?.name === name) {
          selectedConnector.value.config = config
        }
        await fetchConnectors()
      }
      return data.success
    } catch (err) {
      console.error('Failed to update connector:', err)
      return false
    }
  }

  async function addCustomServer(config: { name: string } & ConnectorConfig) {
    try {
      const data = await gatewayService.call<{ success: boolean }>('installConnector', {
        name: config.name,
        config: {
          type: config.type,
          command: config.command,
          args: config.args,
          url: config.url,
          env: config.env,
          description: config.description,
        },
      })
      if (data.success) {
        await fetchConnectors()
      }
      return data.success
    } catch (err) {
      console.error('Failed to add custom server:', err)
      return false
    }
  }

  function clearSelection() {
    selectedConnector.value = null
  }

  return {
    connectors,
    selectedConnector,
    loading,
    searchQuery,
    builtinConnectors,
    customConnectors,
    filteredBuiltinConnectors,
    filteredCustomConnectors,
    fetchConnectors,
    fetchConnectorDetail,
    installConnector,
    uninstallConnector,
    updateConnector,
    addCustomServer,
    clearSelection,
  }
})

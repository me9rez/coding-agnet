<script setup lang="ts">
import {
  ChevronDown,
  ChevronRight,
  Check,
  Loader2,
  Plus,
  Plug,
  Search,
  Settings,
  Trash2,
  X,
} from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useConnectorsStore } from '@/stores/connectors'
import type { Connector, ConnectorConfig } from '@/stores/connectors'
import AddServerModal from './AddServerModal.vue'

const connectorsStore = useConnectorsStore()

const expandedSections = ref({ builtin: true, custom: true })
const selectedConnectorName = ref<string | null>(null)
const showAddModal = ref(false)
const showConfigEditor = ref(false)
const editingConfig = ref<string>('')

onMounted(() => {
  connectorsStore.fetchConnectors()
})

function toggleSection(section: 'builtin' | 'custom') {
  expandedSections.value[section] = !expandedSections.value[section]
}

async function selectConnector(connector: Connector) {
  selectedConnectorName.value = connector.name
  await connectorsStore.fetchConnectorDetail(connector.name)
  showConfigEditor.value = false
}

async function handleInstall(connector: Connector) {
  await connectorsStore.installConnector(connector.name)
}

async function handleUninstall(connector: Connector) {
  if (confirm(`确定卸载连接器 "${connector.name}" 吗？`)) {
    await connectorsStore.uninstallConnector(connector.name)
    selectedConnectorName.value = null
  }
}

function startConfigEdit() {
  if (connectorsStore.selectedConnector) {
    editingConfig.value = JSON.stringify(connectorsStore.selectedConnector.config, null, 2)
    showConfigEditor.value = true
  }
}

function cancelConfigEdit() {
  showConfigEditor.value = false
  editingConfig.value = ''
}

async function saveConfigEdit() {
  if (connectorsStore.selectedConnector) {
    try {
      const config = JSON.parse(editingConfig.value) as ConnectorConfig
      await connectorsStore.updateConnector(connectorsStore.selectedConnector.name, config)
      showConfigEditor.value = false
    } catch (e) {
      alert('JSON 格式错误')
    }
  }
}

function handleAddServer() {
  showAddModal.value = true
}

async function handleServerAdded() {
  showAddModal.value = false
  await connectorsStore.fetchConnectors()
}
</script>

<template>
  <div class="h-full flex">
    <div class="w-64 bg-[var(--bg-page)] border-r border-[var(--border)] flex flex-col">
      <div class="p-3 border-b border-[var(--border)]">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-semibold">连接器</h2>
          <button
            class="p-1.5 rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition"
            title="添加自定义服务器"
            @click="handleAddServer"
          >
            <Plus class="w-5 h-5" />
          </button>
        </div>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-subtle)]" />
          <input
            v-model="connectorsStore.searchQuery"
            type="text"
            placeholder="搜索连接器..."
            class="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-card)] outline-none focus:border-[var(--text-muted)] transition"
          >
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-2">
        <div v-if="connectorsStore.loading" class="flex items-center justify-center py-8">
          <Loader2 class="w-5 h-5 animate-spin text-[var(--text-muted)]" />
        </div>

        <template v-else>
          <div class="mb-2">
            <button
              class="flex items-center gap-2 w-full px-2 py-1.5 text-sm font-medium text-[var(--text-muted)] hover:bg-[var(--bg-muted)] rounded-lg transition"
              @click="toggleSection('builtin')"
            >
              <component :is="expandedSections.builtin ? ChevronDown : ChevronRight" class="w-4 h-4" />
              <Plug class="w-4 h-4" />
              <span>示例</span>
              <span class="ml-auto text-xs">{{ connectorsStore.builtinConnectors.length }}</span>
            </button>
            <ul v-if="expandedSections.builtin" class="ml-4 space-y-0.5">
              <li
                v-for="connector in connectorsStore.filteredBuiltinConnectors"
                :key="connector.name"
              >
                <button
                  class="w-full text-left px-3 py-1.5 rounded-lg text-sm transition flex items-center gap-2"
                  :class="
                    selectedConnectorName === connector.name
                      ? 'bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)]'
                      : 'hover:bg-[var(--bg-muted)]'
                  "
                  @click="selectConnector(connector)"
                >
                  <span class="truncate">{{ connector.name }}</span>
                  <Check
                    v-if="connector.installed"
                    class="w-4 h-4 ml-auto text-green-500"
                  />
                </button>
              </li>
            </ul>
          </div>

          <div v-if="connectorsStore.customConnectors.length > 0">
            <button
              class="flex items-center gap-2 w-full px-2 py-1.5 text-sm font-medium text-[var(--text-muted)] hover:bg-[var(--bg-muted)] rounded-lg transition"
              @click="toggleSection('custom')"
            >
              <component :is="expandedSections.custom ? ChevronDown : ChevronRight" class="w-4 h-4" />
              <Settings class="w-4 h-4" />
              <span>自定义</span>
              <span class="ml-auto text-xs">{{ connectorsStore.customConnectors.length }}</span>
            </button>
            <ul v-if="expandedSections.custom" class="ml-4 space-y-0.5">
              <li
                v-for="connector in connectorsStore.filteredCustomConnectors"
                :key="connector.name"
              >
                <button
                  class="w-full text-left px-3 py-1.5 rounded-lg text-sm transition flex items-center gap-2"
                  :class="
                    selectedConnectorName === connector.name
                      ? 'bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)]'
                      : 'hover:bg-[var(--bg-muted)]'
                  "
                  @click="selectConnector(connector)"
                >
                  <span class="truncate">{{ connector.name }}</span>
                </button>
              </li>
            </ul>
          </div>
        </template>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto bg-[var(--bg-card)]">
      <div v-if="!connectorsStore.selectedConnector" class="h-full flex items-center justify-center text-[var(--text-muted)]">
        <div class="text-center">
          <Plug class="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>选择一个连接器查看详情</p>
        </div>
      </div>

      <div v-else class="p-6">
        <div class="flex items-start justify-between mb-4">
          <div>
            <div class="flex items-center gap-3">
              <Plug class="w-6 h-6 text-[var(--text-muted)]" />
              <h1 class="text-2xl font-bold">{{ connectorsStore.selectedConnector.name }}</h1>
            </div>
          </div>

          <button
            v-if="!connectorsStore.selectedConnector.installed"
            class="px-4 py-2 rounded-lg bg-[var(--text)] text-[var(--bg-card)] text-sm font-medium hover:opacity-90 transition"
            @click="handleInstall(connectorsStore.selectedConnector)"
          >
            + 安装
          </button>
          <button
            v-else
            class="px-4 py-2 rounded-lg border border-[var(--border)] text-sm font-medium hover:bg-[var(--bg-muted)] transition flex items-center gap-2"
            @click="handleUninstall(connectorsStore.selectedConnector)"
          >
            <Trash2 class="w-4 h-4" />
            <span>卸载</span>
          </button>
        </div>

        <div class="mb-6">
          <h3 class="text-sm font-medium text-[var(--text-muted)] mb-2">Description</h3>
          <p class="text-sm">{{ connectorsStore.selectedConnector.description }}</p>
        </div>

        <div v-if="connectorsStore.selectedConnector.config" class="mb-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-medium text-[var(--text-muted)]">配置</h3>
            <button
              v-if="!showConfigEditor"
              class="px-2 py-1 text-xs rounded hover:bg-[var(--bg-muted)] transition"
              @click="startConfigEdit"
            >
              编辑
            </button>
            <div v-else class="flex items-center gap-1">
              <button
                class="px-2 py-1 text-xs rounded hover:bg-[var(--bg-muted)] transition"
                @click="cancelConfigEdit"
              >
                取消
              </button>
              <button
                class="px-2 py-1 text-xs rounded bg-[var(--text)] text-[var(--bg-card)] hover:opacity-90 transition"
                @click="saveConfigEdit"
              >
                保存
              </button>
            </div>
          </div>

          <div
            v-if="showConfigEditor"
            class="border border-[var(--border)] rounded-lg overflow-hidden"
          >
            <textarea
              v-model="editingConfig"
              class="w-full h-64 p-4 text-sm font-mono bg-[var(--bg-page)] outline-none resize-none"
            />
          </div>

          <div
            v-else
            class="border border-[var(--border)] rounded-lg p-4 bg-[var(--bg-page)]"
          >
            <pre class="text-sm font-mono whitespace-pre-wrap">{{ JSON.stringify(connectorsStore.selectedConnector.config, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>

    <AddServerModal
      v-if="showAddModal"
      @close="showAddModal = false"
      @added="handleServerAdded"
    />
  </div>
</template>

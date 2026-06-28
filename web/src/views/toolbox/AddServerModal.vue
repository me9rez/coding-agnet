<script setup lang="ts">
import { Check, X } from '@lucide/vue'
import { ref } from 'vue'
import { useConnectorsStore } from '@/stores/connectors'

const emit = defineEmits<{
  close: []
  added: []
}>()

const connectorsStore = useConnectorsStore()

const activeTab = ref<'form' | 'json'>('form')
const loading = ref(false)

// Form mode
const formName = ref('')
const formType = ref<'stdio' | 'streamable-http'>('stdio')
const formCommand = ref('')
const formArgs = ref('')
const formUrl = ref('')
const formEnv = ref('')

// JSON mode
const jsonConfig = ref(`{
  "server-name": {
    "url": "https://mcp.example.com/mcp"
  }
}`)

async function handleAdd() {
  loading.value = true
  try {
    if (activeTab.value === 'form') {
      const config: Record<string, unknown> = {
        type: formType.value,
      }

      if (formType.value === 'stdio') {
        config.command = formCommand.value
        if (formArgs.value) {
          config.args = formArgs.value.split(/\s+/).filter(Boolean)
        }
      } else {
        config.url = formUrl.value
      }

      if (formEnv.value) {
        try {
          config.env = JSON.parse(formEnv.value)
        } catch {
          alert('环境变量 JSON 格式错误')
          return
        }
      }

      await connectorsStore.addCustomServer({
        name: formName.value,
        ...config,
      } as Parameters<typeof connectorsStore.addCustomServer>[0])
    } else {
      const parsed = JSON.parse(jsonConfig.value)
      const entries = Object.entries(parsed)
      if (entries.length === 0) {
        alert('请输入有效的 JSON 配置')
        return
      }
      const [name, config] = entries[0] as [string, Record<string, unknown>]
      await connectorsStore.addCustomServer({
        name,
        type: config.url ? 'streamable-http' : 'stdio',
        ...config,
      } as Parameters<typeof connectorsStore.addCustomServer>[0])
    }
    emit('added')
  } catch (e) {
    alert('添加失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />
      <div class="relative bg-[var(--bg-card)] rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        <div class="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-[var(--text-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <path d="M8 21h8M12 17v4" />
            </svg>
            <h2 class="text-lg font-semibold">添加自定义服务器</h2>
          </div>
          <button
            class="p-1 rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition"
            @click="emit('close')"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="px-6 py-4">
          <div class="flex border-b border-[var(--border)] mb-4">
            <button
              class="px-4 py-2 text-sm font-medium transition border-b-2"
              :class="
                activeTab === 'form'
                  ? 'border-[var(--text)] text-[var(--text)]'
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
              "
              @click="activeTab = 'form'"
            >
              表单
            </button>
            <button
              class="px-4 py-2 text-sm font-medium transition border-b-2"
              :class="
                activeTab === 'json'
                  ? 'border-[var(--text)] text-[var(--text)]'
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
              "
              @click="activeTab = 'json'"
            >
              JSON
            </button>
          </div>

          <div v-if="activeTab === 'form'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-[var(--text-muted)] mb-1">服务器名称</label>
              <input
                v-model="formName"
                type="text"
                placeholder="服务器名称"
                class="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] transition"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-[var(--text-muted)] mb-1">连接方式</label>
              <div class="flex rounded-lg border border-[var(--border)] overflow-hidden">
                <button
                  class="flex-1 px-3 py-2 text-sm transition"
                  :class="
                    formType === 'stdio'
                      ? 'bg-[var(--text)] text-[var(--bg-card)]'
                      : 'bg-[var(--bg-page)] hover:bg-[var(--bg-muted)]'
                  "
                  @click="formType = 'stdio'"
                >
                  本地进程 (Stdio)
                </button>
                <button
                  class="flex-1 px-3 py-2 text-sm transition"
                  :class="
                    formType === 'streamable-http'
                      ? 'bg-[var(--text)] text-[var(--bg-card)]'
                      : 'bg-[var(--bg-page)] hover:bg-[var(--bg-muted)]'
                  "
                  @click="formType = 'streamable-http'"
                >
                  远程服务 (HTTP)
                </button>
              </div>
            </div>

            <template v-if="formType === 'stdio'">
              <div>
                <label class="block text-sm font-medium text-[var(--text-muted)] mb-1">命令 (如 npx)</label>
                <input
                  v-model="formCommand"
                  type="text"
                  placeholder="命令 (如 npx)"
                  class="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] transition"
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-[var(--text-muted)] mb-1">参数 (空格分隔)</label>
                <input
                  v-model="formArgs"
                  type="text"
                  placeholder="参数 (空格分隔)"
                  class="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] transition"
                >
              </div>
            </template>

            <template v-else>
              <div>
                <label class="block text-sm font-medium text-[var(--text-muted)] mb-1">URL</label>
                <input
                  v-model="formUrl"
                  type="text"
                  placeholder="https://mcp.example.com/mcp"
                  class="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] transition"
                >
              </div>
            </template>

            <div>
              <label class="block text-sm font-medium text-[var(--text-muted)] mb-1">Env (JSON)</label>
              <input
                v-model="formEnv"
                type="text"
                placeholder='{"API_KEY": "..."}'
                class="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] transition"
              >
            </div>
          </div>

          <div v-else>
            <label class="block text-sm font-medium text-[var(--text-muted)] mb-2">粘贴 MCP 服务器 JSON 配置</label>
            <textarea
              v-model="jsonConfig"
              class="w-full h-48 p-3 text-sm font-mono rounded-lg border border-[var(--border)] bg-[var(--bg-page)] outline-none focus:border-[var(--text-muted)] transition resize-none"
            />
            <p class="mt-2 text-xs text-[var(--text-subtle)]">
              JSON 的 key 即为服务器名称，可直接粘贴 Claude Desktop、Cursor 等客户端的配置
            </p>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 px-6 py-4 border-t border-[var(--border)]">
          <button
            class="px-4 py-2 text-sm rounded-lg hover:bg-[var(--bg-muted)] transition"
            @click="emit('close')"
          >
            取消
          </button>
          <button
            class="px-4 py-2 text-sm rounded-lg bg-[var(--text)] text-[var(--bg-card)] font-medium hover:opacity-90 transition flex items-center gap-2 disabled:opacity-50"
            :disabled="loading || (activeTab === 'form' && !formName)"
            @click="handleAdd"
          >
            <Check class="w-4 h-4" />
            <span>添加</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

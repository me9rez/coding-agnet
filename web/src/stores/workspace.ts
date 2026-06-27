import { defineStore } from 'pinia'
import { ref } from 'vue'
import { gatewayService } from '@/services/gateway'
import { isReadyEvent } from '@/types/gateway'
import type { WorkspaceInfo } from '@/types/gateway'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspace = ref<WorkspaceInfo | null>(null)

  function setWorkspace(info: WorkspaceInfo) {
    workspace.value = info
  }

  function setupEventListeners() {
    gatewayService.on('ready', (event) => {
      if (isReadyEvent(event) && event.workspace) {
        setWorkspace(event.workspace)
      }
    })
  }

  return {
    workspace,
    setWorkspace,
    setupEventListeners,
  }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { gatewayService } from '@/services/gateway'
import type { EventListener, ScheduledTask } from '@/types/automation'

export const useAutomationStore = defineStore('automation', () => {
  const tasks = ref<ScheduledTask[]>([])
  const listeners = ref<EventListener[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchTasks() {
    loading.value = true
    error.value = null
    try {
      tasks.value = await gatewayService.call<ScheduledTask[]>('listScheduledTasks')
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: Partial<ScheduledTask>): Promise<ScheduledTask | null> {
    try {
      const task = await gatewayService.call<ScheduledTask>('createScheduledTask', data as Record<string, unknown>)
      tasks.value.push(task)
      return task
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return null
    }
  }

  async function updateTask(id: string, patch: Partial<ScheduledTask>): Promise<ScheduledTask | null> {
    try {
      const task = await gatewayService.call<ScheduledTask>('updateScheduledTask', { id, ...patch } as Record<string, unknown>)
      const idx = tasks.value.findIndex((t) => t.id === id)
      if (idx >= 0) tasks.value[idx] = task
      return task
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return null
    }
  }

  async function deleteTask(id: string): Promise<boolean> {
    try {
      await gatewayService.call<{ ok: boolean }>('deleteScheduledTask', { id })
      tasks.value = tasks.value.filter((t) => t.id !== id)
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function toggleTask(id: string, enabled: boolean): Promise<ScheduledTask | null> {
    try {
      const task = await gatewayService.call<ScheduledTask>('toggleScheduledTask', { id, enabled })
      const idx = tasks.value.findIndex((t) => t.id === id)
      if (idx >= 0) tasks.value[idx] = task
      return task
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return null
    }
  }

  async function fetchListeners() {
    loading.value = true
    error.value = null
    try {
      listeners.value = await gatewayService.call<EventListener[]>('listEventListeners')
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  async function createListener(data: Partial<EventListener>): Promise<EventListener | null> {
    try {
      const listener = await gatewayService.call<EventListener>('createEventListener', data as Record<string, unknown>)
      listeners.value.push(listener)
      return listener
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return null
    }
  }

  async function updateListener(id: string, patch: Partial<EventListener>): Promise<EventListener | null> {
    try {
      const listener = await gatewayService.call<EventListener>('updateEventListener', { id, ...patch } as Record<string, unknown>)
      const idx = listeners.value.findIndex((l) => l.id === id)
      if (idx >= 0) listeners.value[idx] = listener
      return listener
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return null
    }
  }

  async function deleteListener(id: string): Promise<boolean> {
    try {
      await gatewayService.call<{ ok: boolean }>('deleteEventListener', { id })
      listeners.value = listeners.value.filter((l) => l.id !== id)
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function toggleListener(id: string, enabled: boolean): Promise<EventListener | null> {
    try {
      const listener = await gatewayService.call<EventListener>('toggleEventListener', { id, enabled })
      const idx = listeners.value.findIndex((l) => l.id === id)
      if (idx >= 0) listeners.value[idx] = listener
      return listener
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return null
    }
  }

  return {
    tasks,
    listeners,
    loading,
    error,
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    toggleTask,
    fetchListeners,
    createListener,
    updateListener,
    deleteListener,
    toggleListener,
  }
})

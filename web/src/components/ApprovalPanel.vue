<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

function approve(callId: string, remember: boolean) {
  chatStore.sendApprovalResponse(callId, true, remember)
}

function reject(callId: string) {
  chatStore.sendApprovalResponse(callId, false, false)
}

function formatArguments(args: string): string {
  try {
    const parsed = JSON.parse(args)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return args
  }
}
</script>

<template>
  <div v-if="chatStore.pendingApprovals.length > 0" class="approval-panel">
    <div
      v-for="request in chatStore.pendingApprovals"
      :key="request.callId"
      class="approval-card"
    >
      <div class="approval-header">
        <span class="approval-icon">⚠️</span>
        <span class="approval-title">工具调用需要审批</span>
      </div>
      <div class="approval-body">
        <p class="approval-tool">
          <code>{{ request.name }}</code>
        </p>
        <pre class="approval-args">{{ formatArguments(request.arguments) }}</pre>
      </div>
      <div class="approval-actions">
        <button class="btn btn-approve" @click="approve(request.callId, false)">同意</button>
        <button class="btn btn-approve-always" @click="approve(request.callId, true)">
          始终同意
        </button>
        <button class="btn btn-reject" @click="reject(request.callId)">拒绝</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.approval-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 12px 0;
}

.approval-card {
  border: 1px solid #e5a000;
  border-radius: 10px;
  background: #fffbe6;
  padding: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

.approval-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-weight: 600;
  color: #8c6b00;
}

.approval-title {
  font-size: 14px;
}

.approval-body {
  margin-bottom: 12px;
}

.approval-tool {
  margin: 0 0 8px;
  font-size: 13px;
  color: #555;
}

.approval-args {
  margin: 0;
  padding: 10px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 6px;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.approval-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-approve {
  background: #22c55e;
  color: white;
}
.btn-approve:hover {
  background: #16a34a;
}

.btn-approve-always {
  background: #86efac;
  color: #14532d;
}
.btn-approve-always:hover {
  background: #4ade80;
}

.btn-reject {
  background: #ef4444;
  color: white;
}
.btn-reject:hover {
  background: #dc2626;
}
</style>

<script setup lang="ts">
import { ref } from 'vue'

const tabs = ['全部', '本月', '本周', '今日']
const activeTab = ref('全部')

const stats = [
  { label: '请求次数', value: '36' },
  { label: '输入 token', value: '445.4k', sub: 'cache 251.8k' },
  { label: '输出 token', value: '8.3k' },
  { label: '缓存命中率', value: '36%', sub: '453.7k total' },
]

const weekLabels = ['一', '二', '三', '四', '五', '日']
// 53 columns x 7 rows mock heatmap
const heatmapCols = 53
const heatmap = Array.from({ length: heatmapCols }, () =>
  Array.from({ length: 7 }, () => Math.random()),
)
// highlight last few days
heatmap[heatmapCols - 2]![5] = 1
heatmap[heatmapCols - 1]![5] = 0.6

const dailyConsumption = [
  { day: '05/30', value: 100 },
  { day: '', value: 12 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 0 },
  { day: '', value: 22 },
  { day: '06/28', value: 0 },
]

const modelBreakdown = [
  { name: 'skywork-ai/skyclaw...', value: 350.6, max: 400 },
  { name: 'deepseek-v4-flash', value: 64.7, max: 400 },
  { name: 'skywork-ai/skyclaw...', value: 38.4, max: 400 },
]

const skillBreakdown = [
  { name: '—', value: 0, max: 400 },
]
</script>

<template>
  <div class="p-8 max-w-5xl mx-auto">
    <h1 class="text-xl font-semibold mb-6">
      用量
    </h1>

    <div class="flex gap-2 mb-6">
      <button
        v-for="tab in tabs"
        :key="tab"
        class="px-4 py-1.5 rounded-full text-sm transition"
        :class="activeTab === tab
          ? 'bg-[#f3eae4] text-[#c47a5c]'
          : 'text-[var(--text-muted)] hover:bg-[var(--bg-muted)]'"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div
        v-for="stat in stats"
        :key="stat.label"
        class="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 shadow-[var(--shadow)]"
      >
        <div class="text-sm text-[var(--text-muted)] mb-2">
          {{ stat.label }}
        </div>
        <div class="text-3xl font-semibold">
          {{ stat.value }}
        </div>
        <div v-if="stat.sub" class="text-xs text-[var(--text-subtle)] mt-1">
          {{ stat.sub }}
        </div>
      </div>
    </div>

    <div class="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow)] mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-base font-medium">
          活跃热图（近 1 年）
        </h2>
        <div class="flex items-center gap-2 text-xs text-[var(--text-subtle)]">
          <span>少</span>
          <div class="flex gap-1">
            <div class="w-3 h-3 rounded-sm bg-[var(--bg-muted)]" />
            <div class="w-3 h-3 rounded-sm bg-[#f3e0d8]" />
            <div class="w-3 h-3 rounded-sm bg-[#e8b4a0]" />
            <div class="w-3 h-3 rounded-sm bg-[#d9896d]" />
            <div class="w-3 h-3 rounded-sm bg-[#c46b4d]" />
          </div>
          <span>多</span>
        </div>
      </div>
      <div class="flex gap-4">
        <div class="flex flex-col justify-between text-xs text-[var(--text-subtle)] py-0.5">
          <span v-for="label in weekLabels" :key="label">{{ label }}</span>
        </div>
        <div class="flex gap-1 overflow-x-auto pb-1">
          <div v-for="(col, cIdx) in heatmap" :key="cIdx" class="flex flex-col gap-1">
            <div
              v-for="(cell, rIdx) in col"
              :key="rIdx"
              class="w-3 h-3 rounded-sm"
              :style="{ backgroundColor: cell <= 0.2 ? 'var(--bg-muted)' : cell <= 0.4 ? '#f3e0d8' : cell <= 0.6 ? '#e8b4a0' : cell <= 0.8 ? '#d9896d' : '#c46b4d' }"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow)] mb-6">
      <h2 class="text-base font-medium mb-6">
        每日消耗（近 30 天）
      </h2>
      <div class="flex items-end justify-between h-32 gap-1">
        <div
          v-for="(d, idx) in dailyConsumption"
          :key="idx"
          class="flex flex-col items-center gap-1 flex-1"
        >
          <div
            class="w-full max-w-6 rounded-t bg-[#e8b4a0] opacity-80"
            :style="{ height: `${Math.max(d.value, 2)}%` }"
          />
          <span v-if="d.day" class="text-[10px] text-[var(--text-subtle)]">{{ d.day }}</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow)]">
        <h2 class="text-sm font-medium text-[var(--text-subtle)] mb-5">
          按 MODEL
        </h2>
        <div class="space-y-4">
          <div v-for="item in modelBreakdown" :key="item.name" class="flex items-center gap-3">
            <span class="w-40 text-sm truncate">{{ item.name }}</span>
            <div class="flex-1 h-2 bg-[var(--bg-muted)] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-[#d9896d]"
                :style="{ width: `${(item.value / item.max) * 100}%` }"
              />
            </div>
            <span class="w-14 text-right text-sm text-[var(--text-muted)]">{{ item.value }}k</span>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow)]">
        <h2 class="text-sm font-medium text-[var(--text-subtle)] mb-5">
          按 SKILL
        </h2>
        <div class="space-y-4">
          <div v-for="item in skillBreakdown" :key="item.name" class="flex items-center gap-3">
            <span class="w-40 text-sm truncate">{{ item.name }}</span>
            <div class="flex-1 h-2 bg-[var(--bg-muted)] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-[#d9896d]"
                :style="{ width: `${(item.value / item.max) * 100}%` }"
              />
            </div>
            <span class="w-14 text-right text-sm text-[var(--text-muted)]">{{ item.value }}k</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

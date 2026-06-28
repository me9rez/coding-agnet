<script setup lang="ts">
import { DynamicScroller, DynamicScrollerItem } from 'vue-virtual-scroller'
import { nextTick, ref, watch } from 'vue'
import MessageItem from '@/components/chat/MessageItem.vue'
import { useChatStore } from '@/stores/chat'
import type { DynamicScrollerExposed } from 'vue-virtual-scroller'
import type { UiMessage } from '@/types/session'

const chatStore = useChatStore()
const scrollerRef = ref<DynamicScrollerExposed<UiMessage> | null>(null)

function scrollToBottom() {
  scrollerRef.value?.scrollToBottom()
}

watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    scrollToBottom()
  },
)

watch(
  () => chatStore.messages[chatStore.messages.length - 1]?.content,
  async () => {
    await nextTick()
    scrollToBottom()
  },
)

function sizeDependencies(message: UiMessage) {
  return [
    message.content,
    message.thinking,
    message.loading,
    message.toolExecution?.output,
    message.toolCall?.arguments,
  ]
}
</script>

<template>
  <div class="h-full overflow-hidden">
    <DynamicScroller
      ref="scrollerRef"
      class="h-full px-12 py-8"
      :items="chatStore.messages"
      key-field="id"
      :min-item-size="80"
    >
      <template #default="{ item, index, active }">
        <DynamicScrollerItem
          :item="item"
          :active="active"
          :data-index="index"
          :size-dependencies="sizeDependencies(item)"
          class="pb-6"
        >
          <MessageItem :message="item" />
        </DynamicScrollerItem>
      </template>
    </DynamicScroller>
  </div>
</template>

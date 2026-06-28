<script setup lang="ts">
import {
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  Edit,
  File,
  Folder,
  FolderOpen,
  Loader2,
  MessageSquare,
  MoreVertical,
  Package,
  Search,
  Trash2,
  User,
} from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSkillsStore } from '@/stores/skills'
import type { Skill, SkillFile } from '@/stores/skills'

const skillsStore = useSkillsStore()
const router = useRouter()

const expandedSections = ref({ builtin: true, mine: true })
const selectedSkillName = ref<string | null>(null)
const expandedSkills = ref<Set<string>>(new Set())
const showMenuFor = ref<string | null>(null)
const editingContent = ref('')
const isEditing = ref(false)
const expandedFolders = ref<Set<string>>(new Set())
const selectedFilePath = ref<string | null>(null)

onMounted(() => {
  skillsStore.fetchSkills()
})

function toggleSection(section: 'builtin' | 'mine') {
  expandedSections.value[section] = !expandedSections.value[section]
}

async function selectSkill(skill: Skill) {
  selectedSkillName.value = skill.name
  expandedFolders.value.clear()
  await Promise.all([
    skillsStore.fetchSkillDetail(skill.name),
    skillsStore.fetchSkillFiles(skill.name),
  ])
  isEditing.value = false
}

async function toggleSkillExpand(skill: Skill, event: MouseEvent) {
  event.stopPropagation()
  const name = skill.name
  if (expandedSkills.value.has(name)) {
    expandedSkills.value.delete(name)
  } else {
    expandedSkills.value.add(name)
    if (!skillsStore.skillFilesMap.has(name)) {
      await skillsStore.fetchSkillFiles(name)
    }
  }
}

function toggleFolder(path: string) {
  if (expandedFolders.value.has(path)) {
    expandedFolders.value.delete(path)
  } else {
    expandedFolders.value.add(path)
  }
}

async function selectFile(skillName: string, filePath: string, event: MouseEvent) {
  event.stopPropagation()
  if (selectedSkillName.value !== skillName) {
    await skillsStore.fetchSkillDetail(skillName)
    selectedSkillName.value = skillName
  }
  selectedFilePath.value = filePath
  await skillsStore.fetchSkillFileContent(skillName, filePath)
}

function startEdit() {
  if (skillsStore.selectedSkill) {
    editingContent.value = skillsStore.selectedSkill.content
    isEditing.value = true
  }
  closeContextMenu()
}

async function saveEdit() {
  if (skillsStore.selectedSkill) {
    await skillsStore.updateSkill(skillsStore.selectedSkill.name, editingContent.value)
    isEditing.value = false
  }
}

function cancelEdit() {
  isEditing.value = false
  editingContent.value = ''
}

async function handleToggle(skill: Skill) {
  await skillsStore.toggleSkill(skill.name, !skill.enabled)
}

async function handleUninstall(skill: Skill) {
  closeContextMenu()
  if (confirm(`确定卸载技能 "${skill.name}" 吗？`)) {
    await skillsStore.uninstallSkill(skill.name)
    selectedSkillName.value = null
  }
}

function handleUseInChat() {
  closeContextMenu()
  router.push('/')
}

function handleExport() {
  closeContextMenu()
}

function handleViewHistory() {
  closeContextMenu()
}

function showContextMenu(name: string, event: MouseEvent) {
  event.preventDefault()
  event.stopPropagation()
  showMenuFor.value = showMenuFor.value === name ? null : name
}

function closeContextMenu() {
  showMenuFor.value = null
}
</script>

<template>
  <div class="h-full flex" @click="closeContextMenu">
    <div class="w-72 bg-[var(--bg-page)] border-r border-[var(--border)] flex flex-col">
      <div class="p-3 border-b border-[var(--border)]">
        <h2 class="text-lg font-semibold mb-3">技能</h2>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-subtle)]" />
          <input
            v-model="skillsStore.searchQuery"
            type="text"
            placeholder="搜索技能..."
            class="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg-card)] outline-none focus:border-[var(--text-muted)] transition"
          >
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-2">
        <div v-if="skillsStore.loading" class="flex items-center justify-center py-8">
          <Loader2 class="w-5 h-5 animate-spin text-[var(--text-muted)]" />
        </div>

        <template v-else>
          <div class="mb-2">
            <button
              class="flex items-center gap-2 w-full px-2 py-1.5 text-sm font-medium text-[var(--text-muted)] hover:bg-[var(--bg-muted)] rounded-lg transition"
              @click="toggleSection('mine')"
            >
              <component :is="expandedSections.mine ? ChevronDown : ChevronRight" class="w-4 h-4" />
              <User class="w-4 h-4" />
              <span>我的</span>
              <span class="ml-auto text-xs">{{ skillsStore.mineSkills.length }}</span>
            </button>
            <ul v-if="expandedSections.mine" class="ml-2 space-y-0.5">
              <li
                v-for="skill in skillsStore.filteredMineSkills"
                :key="skill.name"
              >
                <div class="flex items-center">
                  <button
                    class="flex-1 text-left px-2 py-1.5 rounded-lg text-sm transition flex items-center gap-2"
                    :class="
                      selectedSkillName === skill.name
                        ? 'bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)]'
                        : 'hover:bg-[var(--bg-muted)]'
                    "
                    @click="selectSkill(skill)"
                  >
                    <Package class="w-4 h-4 shrink-0 text-[var(--text-subtle)]" />
                    <span class="truncate">{{ skill.name }}</span>
                  </button>
                  <button
                    class="p-1 rounded hover:bg-[var(--bg-muted)] transition"
                    @click="toggleSkillExpand(skill, $event)"
                  >
                    <ChevronRight
                      class="w-3 h-3 transition-transform"
                      :class="expandedSkills.has(skill.name) ? 'rotate-90' : ''"
                    />
                  </button>
                </div>
                <ul
                  v-if="expandedSkills.has(skill.name) && skillsStore.skillFilesMap.get(skill.name)"
                  class="ml-4 space-y-0.5"
                >
                  <li v-for="item in skillsStore.skillFilesMap.get(skill.name)" :key="item.path">
                    <div
                      v-if="item.type === 'directory'"
                    >
                      <button
                        class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                        @click="toggleFolder(item.path)"
                      >
                        <component
                          :is="expandedFolders.has(item.path) ? FolderOpen : Folder"
                          class="w-4 h-4 shrink-0 text-yellow-500"
                        />
                        <span class="truncate">{{ item.name }}</span>
                      </button>
                      <ul
                        v-if="expandedFolders.has(item.path) && item.children"
                        class="ml-4 space-y-0.5"
                      >
                        <li v-for="child in item.children" :key="child.path">
                          <div
                            v-if="child.type === 'directory'"
                          >
                            <button
                              class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                              @click="toggleFolder(child.path)"
                            >
                              <component
                                :is="expandedFolders.has(child.path) ? FolderOpen : Folder"
                                class="w-4 h-4 shrink-0 text-yellow-500"
                              />
                              <span class="truncate">{{ child.name }}</span>
                            </button>
                          </div>
                          <button
                            v-else
                            class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                            :class="selectedFilePath === child.path ? 'bg-[var(--bg-card)]' : ''"
                            @click="selectFile(skill.name, child.path, $event)"
                          >
                            <File class="w-4 h-4 shrink-0 text-[var(--text-subtle)]" />
                            <span class="truncate">{{ child.name }}</span>
                          </button>
                        </li>
                      </ul>
                    </div>
                    <button
                      v-else
                      class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                      :class="selectedFilePath === item.path ? 'bg-[var(--bg-card)]' : ''"
                      @click="selectFile(skill.name, item.path, $event)"
                    >
                      <File class="w-4 h-4 shrink-0 text-[var(--text-subtle)]" />
                      <span class="truncate">{{ item.name }}</span>
                    </button>
                  </li>
                </ul>
              </li>
            </ul>
          </div>

          <div>
            <button
              class="flex items-center gap-2 w-full px-2 py-1.5 text-sm font-medium text-[var(--text-muted)] hover:bg-[var(--bg-muted)] rounded-lg transition"
              @click="toggleSection('builtin')"
            >
              <component :is="expandedSections.builtin ? ChevronDown : ChevronRight" class="w-4 h-4" />
              <Package class="w-4 h-4" />
              <span>内置</span>
              <span class="ml-auto text-xs">{{ skillsStore.builtinSkills.length }}</span>
            </button>
            <ul v-if="expandedSections.builtin" class="ml-2 space-y-0.5">
              <li
                v-for="skill in skillsStore.filteredBuiltinSkills"
                :key="skill.name"
              >
                <div class="flex items-center">
                  <button
                    class="flex-1 text-left px-2 py-1.5 rounded-lg text-sm transition flex items-center gap-2"
                    :class="
                      selectedSkillName === skill.name
                        ? 'bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow)]'
                        : 'hover:bg-[var(--bg-muted)]'
                    "
                    @click="selectSkill(skill)"
                  >
                    <Package class="w-4 h-4 shrink-0 text-[var(--text-subtle)]" />
                    <span class="truncate">{{ skill.name }}</span>
                  </button>
                  <button
                    class="p-1 rounded hover:bg-[var(--bg-muted)] transition"
                    @click="toggleSkillExpand(skill, $event)"
                  >
                    <ChevronRight
                      class="w-3 h-3 transition-transform"
                      :class="expandedSkills.has(skill.name) ? 'rotate-90' : ''"
                    />
                  </button>
                </div>
                <ul
                  v-if="expandedSkills.has(skill.name) && skillsStore.skillFilesMap.get(skill.name)"
                  class="ml-4 space-y-0.5"
                >
                  <li v-for="item in skillsStore.skillFilesMap.get(skill.name)" :key="item.path">
                    <div
                      v-if="item.type === 'directory'"
                    >
                      <button
                        class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                        @click="toggleFolder(item.path)"
                      >
                        <component
                          :is="expandedFolders.has(item.path) ? FolderOpen : Folder"
                          class="w-4 h-4 shrink-0 text-yellow-500"
                        />
                        <span class="truncate">{{ item.name }}</span>
                      </button>
                      <ul
                        v-if="expandedFolders.has(item.path) && item.children"
                        class="ml-4 space-y-0.5"
                      >
                        <li v-for="child in item.children" :key="child.path">
                          <div
                            v-if="child.type === 'directory'"
                          >
                            <button
                              class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                              @click="toggleFolder(child.path)"
                            >
                              <component
                                :is="expandedFolders.has(child.path) ? FolderOpen : Folder"
                                class="w-4 h-4 shrink-0 text-yellow-500"
                              />
                              <span class="truncate">{{ child.name }}</span>
                            </button>
                          </div>
                          <button
                            v-else
                            class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                            :class="selectedFilePath === child.path ? 'bg-[var(--bg-card)]' : ''"
                            @click="selectFile(skill.name, child.path, $event)"
                          >
                            <File class="w-4 h-4 shrink-0 text-[var(--text-subtle)]" />
                            <span class="truncate">{{ child.name }}</span>
                          </button>
                        </li>
                      </ul>
                    </div>
                    <button
                      v-else
                      class="w-full text-left px-2 py-1 rounded text-sm transition flex items-center gap-1.5 hover:bg-[var(--bg-muted)]"
                      :class="selectedFilePath === item.path ? 'bg-[var(--bg-card)]' : ''"
                      @click="selectFile(skill.name, item.path, $event)"
                    >
                      <File class="w-4 h-4 shrink-0 text-[var(--text-subtle)]" />
                      <span class="truncate">{{ item.name }}</span>
                    </button>
                  </li>
                </ul>
              </li>
            </ul>
          </div>
        </template>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto bg-[var(--bg-card)]">
      <div v-if="!skillsStore.selectedSkill" class="h-full flex items-center justify-center text-[var(--text-muted)]">
        <div class="text-center">
          <p>选择一个技能查看详情</p>
        </div>
      </div>

      <div v-else class="h-full flex flex-col">
        <div class="p-6 pb-4">
          <div class="flex items-start justify-between">
            <div>
              <h1 class="text-2xl font-bold">{{ skillsStore.selectedSkill.name }}</h1>
              <div class="flex items-center gap-2 mt-1">
                <span class="text-sm text-[var(--text-muted)]">来源</span>
                <span
                  class="px-2 py-0.5 text-xs rounded-full"
                  :class="
                    skillsStore.selectedSkill.source === 'builtin'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-green-100 text-green-700'
                  "
                >
                  {{ skillsStore.selectedSkill.source === 'builtin' ? '内置' : '全局安装' }}
                </span>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <button
                class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                :class="skillsStore.selectedSkill.enabled ? 'bg-orange-500' : 'bg-gray-300'"
                title="启用/禁用"
                @click="handleToggle(skillsStore.selectedSkill)"
              >
                <span
                  class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform"
                  :class="skillsStore.selectedSkill.enabled ? 'translate-x-4' : 'translate-x-0.5'"
                />
              </button>

              <div class="relative">
                <button
                  class="p-2 rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-muted)] transition"
                  title="更多操作"
                  @click="showContextMenu(skillsStore.selectedSkill.name, $event)"
                >
                  <MoreVertical class="w-5 h-5" />
                </button>

                <div
                  v-if="showMenuFor === skillsStore.selectedSkill.name"
                  class="absolute right-0 top-full mt-1 w-48 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg shadow-lg py-1 z-10"
                >
                  <button
                    class="w-full text-left px-3 py-2 text-sm hover:bg-[var(--bg-muted)] transition flex items-center gap-2"
                    @click="handleUseInChat"
                  >
                    <MessageSquare class="w-4 h-4" />
                    <span>去对话中使用</span>
                  </button>
                  <button
                    class="w-full text-left px-3 py-2 text-sm hover:bg-[var(--bg-muted)] transition flex items-center gap-2"
                    @click="handleExport"
                  >
                    <Download class="w-4 h-4" />
                    <span>导出技能包</span>
                  </button>
                  <button
                    class="w-full text-left px-3 py-2 text-sm hover:bg-[var(--bg-muted)] transition flex items-center gap-2"
                    @click="handleViewHistory"
                  >
                    <Clock class="w-4 h-4" />
                    <span>查看历史</span>
                  </button>
                  <button
                    class="w-full text-left px-3 py-2 text-sm hover:bg-[var(--bg-muted)] transition flex items-center gap-2"
                    @click="startEdit"
                  >
                    <Edit class="w-4 h-4" />
                    <span>编辑</span>
                  </button>
                  <button
                    v-if="skillsStore.selectedSkill.source === 'mine'"
                    class="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-[var(--bg-muted)] transition flex items-center gap-2"
                    @click="handleUninstall(skillsStore.selectedSkill)"
                  >
                    <Trash2 class="w-4 h-4" />
                    <span>卸载</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex-1 px-6 pb-6 min-h-0">
          <div class="h-full flex flex-col border border-[var(--border)] rounded-lg overflow-hidden">
            <div class="flex items-center justify-between px-4 py-2 bg-[var(--bg-page)] border-b border-[var(--border)]">
              <span class="text-sm font-medium text-[var(--text-muted)]">{{ selectedFilePath || 'SKILL.md' }}</span>
              <div v-if="!isEditing && !selectedFilePath">
                <button
                  class="px-2 py-1 text-xs rounded hover:bg-[var(--bg-muted)] transition"
                  @click="startEdit"
                >
                  编辑
                </button>
              </div>
              <div v-else-if="isEditing" class="flex items-center gap-1">
                <button
                  class="px-2 py-1 text-xs rounded hover:bg-[var(--bg-muted)] transition"
                  @click="cancelEdit"
                >
                  取消
                </button>
                <button
                  class="px-2 py-1 text-xs rounded bg-[var(--text)] text-[var(--bg-card)] hover:opacity-90 transition"
                  @click="saveEdit"
                >
                  保存
                </button>
              </div>
              <div v-else-if="selectedFilePath">
                <button
                  class="px-2 py-1 text-xs rounded hover:bg-[var(--bg-muted)] transition"
                  @click="selectedFilePath = null"
                >
                  返回 SKILL.md
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-auto">
              <textarea
                v-if="isEditing"
                v-model="editingContent"
                class="w-full h-full p-4 text-sm font-mono bg-white outline-none resize-none"
              />
              <pre
                v-else-if="selectedFilePath"
                class="p-4 text-sm whitespace-pre-wrap font-mono"
              >{{ skillsStore.currentFileContent || '无内容' }}</pre>
              <pre
                v-else
                class="p-4 text-sm whitespace-pre-wrap font-mono"
              >{{ skillsStore.selectedSkill.content || '无内容' }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

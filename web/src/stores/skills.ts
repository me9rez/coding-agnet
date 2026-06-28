import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { gatewayService } from '@/services/gateway'

export interface Skill {
  name: string
  source: 'builtin' | 'mine'
  description: string
  enabled: boolean
  path: string
}

export interface SkillDetail extends Skill {
  content: string
}

export interface SkillFile {
  name: string
  type: 'file' | 'directory'
  path: string
  children?: SkillFile[]
}

export const useSkillsStore = defineStore('skills', () => {
  const skills = ref<Skill[]>([])
  const selectedSkill = ref<SkillDetail | null>(null)
  const skillFiles = ref<SkillFile[]>([])
  const skillFilesMap = ref<Map<string, SkillFile[]>>(new Map())
  const currentFileContent = ref<string>('')
  const currentFilePath = ref<string>('')
  const loading = ref(false)
  const searchQuery = ref('')

  const builtinSkills = computed(() =>
    skills.value.filter((s) => s.source === 'builtin').sort((a, b) => a.name.localeCompare(b.name)),
  )

  const mineSkills = computed(() =>
    skills.value.filter((s) => s.source === 'mine').sort((a, b) => a.name.localeCompare(b.name)),
  )

  const filteredBuiltinSkills = computed(() => {
    if (!searchQuery.value) return builtinSkills.value
    const q = searchQuery.value.toLowerCase()
    return builtinSkills.value.filter((s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q))
  })

  const filteredMineSkills = computed(() => {
    if (!searchQuery.value) return mineSkills.value
    const q = searchQuery.value.toLowerCase()
    return mineSkills.value.filter((s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q))
  })

  async function fetchSkills() {
    loading.value = true
    try {
      const data = await gatewayService.call<{ skills: Skill[] }>('listSkills')
      skills.value = data.skills || []
    } catch (err) {
      console.error('Failed to fetch skills:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchSkillDetail(name: string) {
    try {
      const data = await gatewayService.call<SkillDetail>('getSkill', { name })
      selectedSkill.value = data
      return data
    } catch (err) {
      console.error('Failed to fetch skill detail:', err)
      return null
    }
  }

  async function fetchSkillFiles(name: string) {
    try {
      const data = await gatewayService.call<{ files: SkillFile[] }>('getSkillFiles', { name })
      const files = data.files || []
      skillFiles.value = files
      skillFilesMap.value.set(name, files)
      return files
    } catch (err) {
      console.error('Failed to fetch skill files:', err)
      return []
    }
  }

  async function fetchSkillFileContent(skillName: string, filePath: string) {
    try {
      const data = await gatewayService.call<{ content: string }>('getSkillFileContent', {
        name: skillName,
        filePath,
      })
      currentFileContent.value = data.content || ''
      currentFilePath.value = filePath
      return data.content
    } catch (err) {
      console.error('Failed to fetch skill file content:', err)
      return null
    }
  }

  async function installSkill(name: string, sourceDir?: string) {
    try {
      const data = await gatewayService.call<{ success: boolean; skill: Skill }>('installSkill', {
        name,
        sourceDir,
      })
      if (data.success) {
        await fetchSkills()
      }
      return data.success
    } catch (err) {
      console.error('Failed to install skill:', err)
      return false
    }
  }

  async function uninstallSkill(name: string) {
    try {
      const data = await gatewayService.call<{ success: boolean }>('uninstallSkill', { name })
      if (data.success) {
        if (selectedSkill.value?.name === name) {
          selectedSkill.value = null
        }
        await fetchSkills()
      }
      return data.success
    } catch (err) {
      console.error('Failed to uninstall skill:', err)
      return false
    }
  }

  async function toggleSkill(name: string, enabled: boolean) {
    try {
      const data = await gatewayService.call<{ success: boolean }>('toggleSkill', { name, enabled })
      if (data.success) {
        await fetchSkills()
        if (selectedSkill.value?.name === name) {
          selectedSkill.value.enabled = enabled
        }
      }
      return data.success
    } catch (err) {
      console.error('Failed to toggle skill:', err)
      return false
    }
  }

  async function updateSkill(name: string, content: string) {
    try {
      const data = await gatewayService.call<{ success: boolean }>('updateSkill', { name, content })
      if (data.success && selectedSkill.value?.name === name) {
        selectedSkill.value.content = content
      }
      return data.success
    } catch (err) {
      console.error('Failed to update skill:', err)
      return false
    }
  }

  function clearSelection() {
    selectedSkill.value = null
  }

  return {
    skills,
    selectedSkill,
    skillFiles,
    skillFilesMap,
    currentFileContent,
    currentFilePath,
    loading,
    searchQuery,
    builtinSkills,
    mineSkills,
    filteredBuiltinSkills,
    filteredMineSkills,
    fetchSkills,
    fetchSkillDetail,
    fetchSkillFiles,
    fetchSkillFileContent,
    installSkill,
    uninstallSkill,
    toggleSkill,
    updateSkill,
    clearSelection,
  }
})

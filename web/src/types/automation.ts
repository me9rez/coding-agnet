export interface ScheduledTask {
  id: string
  name: string
  description: string
  command: string
  frequency: 'hourly' | 'daily' | 'weekly' | 'weekdays' | 'manual'
  timeHour: number
  timeMinute: number
  skill: string
  project: string
  workspacePath: string
  pushChannel: string
  enabled: boolean
  runCount: number
  createdAt: string
  updatedAt: string
}

export interface EventListener {
  id: string
  name: string
  description: string
  triggerType: 'http' | 'file_change' | 'scheduled' | 'im_message'
  command: string
  triggerCondition: 'all' | 'keyword' | 'regex'
  debounceSeconds: number
  quietHours: boolean
  pushResult: boolean
  skill: string
  project: string
  enabled: boolean
  runCount: number
  createdAt: string
  updatedAt: string
  // file_change specific
  watchPath: string
  watchEvents: string[]
  fileNamePattern: string
  // scheduled specific
  intervalSeconds: number
  // im_message specific
  imChannel: string
  imScope: 'mention' | 'private' | 'all'
  groupId: string
  senderMatch: string
}

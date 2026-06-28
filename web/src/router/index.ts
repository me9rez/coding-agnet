import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import SettingsLayout from '../views/settings/SettingsLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: ChatView,
    },
    {
      path: '/settings',
      component: SettingsLayout,
      redirect: '/settings/usage',
      children: [
        {
          path: 'usage',
          name: 'settings-usage',
          component: () => import('../views/settings/SettingsUsageView.vue'),
        },
        {
          path: 'models',
          name: 'settings-models',
          component: () => import('../views/settings/SettingsModelsView.vue'),
        },
        {
          path: 'channels',
          name: 'settings-channels',
          component: () => import('../views/settings/SettingsChannelsView.vue'),
        },
        {
          path: 'memory',
          name: 'settings-memory',
          component: () => import('../views/settings/SettingsMemoryView.vue'),
        },
        {
          path: 'personality',
          name: 'settings-personality',
          component: () => import('../views/settings/SettingsPersonalityView.vue'),
        },
        {
          path: 'security',
          name: 'settings-security',
          component: () => import('../views/settings/SettingsSecurityView.vue'),
        },
        {
          path: 'preferences',
          name: 'settings-preferences',
          component: () => import('../views/settings/SettingsPreferencesView.vue'),
        },
        {
          path: 'diagnostics',
          name: 'settings-diagnostics',
          component: () => import('../views/settings/SettingsDiagnosticsView.vue'),
        },
        {
          path: 'feedback',
          name: 'settings-feedback',
          component: () => import('../views/settings/SettingsFeedbackView.vue'),
        },
        {
          path: 'version',
          name: 'settings-version',
          component: () => import('../views/settings/SettingsVersionView.vue'),
        },
      ],
    },
  ],
})

export default router

import { createRouter, createWebHashHistory } from 'vue-router'
import CadreCardListView from './views/CadreCardListView.vue'
import CadreCardDetailView from './views/CadreCardDetailView.vue'
import ScheduleListView from './views/ScheduleListView.vue'
import ScheduleEditView from './views/ScheduleEditView.vue'
import BackupView from './views/BackupView.vue'
import PublishSettingsView from './views/PublishSettingsView.vue'
import GuideView from './views/GuideView.vue'

// hash 模式：GitHub Pages 靜態托管時免伺服器端 rewrite，重新整理不會 404。
const routes = [
  { path: '/', redirect: { name: 'cadre-list' } },
  { path: '/cadre', name: 'cadre-list', component: CadreCardListView },
  { path: '/cadre/card/:id', name: 'cadre-card', component: CadreCardDetailView, props: true },
  { path: '/cadre/schedules', name: 'schedule-list', component: ScheduleListView },
  { path: '/cadre/schedule/:id', name: 'schedule-edit', component: ScheduleEditView, props: true },
  { path: '/cadre/backup', name: 'backup', component: BackupView },
  { path: '/cadre/publish-settings', name: 'publish-settings', component: PublishSettingsView },
  { path: '/guide', name: 'guide', component: GuideView },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})

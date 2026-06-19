import { createRouter, createWebHashHistory } from 'vue-router'
import SpaListView from './views/SpaListView.vue'
import SpaBoardView from './views/SpaBoardView.vue'
import CardDetailView from './views/CardDetailView.vue'
import StoreCardListView from './views/StoreCardListView.vue'
import StoreCardDetailView from './views/StoreCardDetailView.vue'
import ScheduleListView from './views/ScheduleListView.vue'
import ScheduleEditView from './views/ScheduleEditView.vue'
import PublishSettingsView from './views/PublishSettingsView.vue'

// 用 hash 模式：打包後由 FastAPI StaticFiles 提供，免伺服器端 rewrite，重新整理不會 404。
const routes = [
  { path: '/', name: 'spa-list', component: SpaListView },
  { path: '/spa/:id', name: 'spa-board', component: SpaBoardView, props: true },
  { path: '/card/:id', name: 'card-detail', component: CardDetailView, props: true },
  { path: '/store', name: 'store-list', component: StoreCardListView },
  { path: '/store/card/:id', name: 'store-card', component: StoreCardDetailView, props: true },
  { path: '/store/schedules', name: 'schedule-list', component: ScheduleListView },
  { path: '/store/schedule/:id', name: 'schedule-edit', component: ScheduleEditView, props: true },
  { path: '/store/publish', name: 'publish-settings', component: PublishSettingsView },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})

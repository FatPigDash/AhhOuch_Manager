import { createRouter, createWebHashHistory } from 'vue-router'
import SpaListView from './views/SpaListView.vue'
import SpaBoardView from './views/SpaBoardView.vue'

// 用 hash 模式：打包後由 FastAPI StaticFiles 提供，免伺服器端 rewrite，重新整理不會 404。
const routes = [
  { path: '/', name: 'spa-list', component: SpaListView },
  { path: '/spa/:id', name: 'spa-board', component: SpaBoardView, props: true },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})

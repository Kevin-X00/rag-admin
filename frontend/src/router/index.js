import { createRouter, createWebHistory } from 'vue-router'
import Overview from '../views/Overview.vue'
import KnowledgeBases from '../views/KnowledgeBases.vue'
import KbDetail from '../views/KbDetail.vue'
import QATest from '../views/QATest.vue'

const routes = [
  { path: '/', name: 'Overview', component: Overview },
  { path: '/knowledge-bases', name: 'KnowledgeBases', component: KnowledgeBases },
  { path: '/knowledge-bases/:id', name: 'KbDetail', component: KbDetail, props: true },
  { path: '/qa-test', name: 'QATest', component: QATest },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

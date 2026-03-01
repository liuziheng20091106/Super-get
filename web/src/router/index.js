import { createRouter, createWebHistory } from 'vue-router'
import Search from '../views/Search.vue'
import Books from '../views/Books.vue'
import Chapters from '../views/Chapters.vue'
import Downloads from '../views/Downloads.vue'
import Settings from '../views/Settings.vue'

const routes = [
  { path: '/', redirect: '/search' },
  { path: '/search', name: 'Search', component: Search },
  { path: '/books', name: 'Books', component: Books },
  { path: '/chapters/:id', name: 'Chapters', component: Chapters },
  { path: '/downloads', name: 'Downloads', component: Downloads },
  { path: '/settings', name: 'Settings', component: Settings }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

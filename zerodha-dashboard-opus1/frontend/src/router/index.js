import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Accounts from '@/views/Accounts.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/accounts',
    name: 'Accounts',
    component: Accounts
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

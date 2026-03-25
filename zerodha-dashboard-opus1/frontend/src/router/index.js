import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Accounts from '@/views/Accounts.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard/overview'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    redirect: '/dashboard/overview',
    children: [
      {
        path: 'overview',
        name: 'Overview',
        component: () => import('@/views/dashboard/OverviewTab.vue')
      },
      {
        path: 'stocks',
        name: 'Stocks',
        component: () => import('@/views/dashboard/StocksTab.vue')
      },
      {
        path: 'mutual-funds',
        name: 'MutualFunds',
        component: () => import('@/views/dashboard/MutualFundsTab.vue')
      },
      {
        path: 'us-stocks',
        name: 'USStocks',
        component: () => import('@/views/dashboard/USStocksTab.vue')
      },
      {
        path: 'fixed-deposits',
        name: 'FixedDeposits',
        component: () => import('@/views/dashboard/FixedDepositsTab.vue')
      }
    ]
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

import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Accounts from '@/views/Accounts.vue'
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true }
  },
  {
    path: '/',
    redirect: '/dashboard/overview'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true },
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
        path: 'eu-stocks',
        name: 'EUStocks',
        component: () => import('@/views/dashboard/EUStocksTab.vue')
      },
      {
        path: 'fixed-deposits',
        name: 'FixedDeposits',
        component: () => import('@/views/dashboard/FixedDepositsTab.vue')
      },
      {
        path: 'bank-balances',
        name: 'BankBalances',
        component: () => import('@/views/dashboard/BankBalancesTab.vue'),
        meta: { requiresAuth: true }
      }
    ]
  },
  {
    path: '/accounts',
    name: 'Accounts',
    component: Accounts,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async to => {
  const authStore = useAuthStore()

  if (!authStore.authReady) {
    await authStore.initializeAuth()
  }

  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const requiresGuest = to.matched.some(record => record.meta.requiresGuest)

  if (requiresAuth && !authStore.isAuthenticated) {
    return {
      path: '/login',
      query: to.fullPath === '/' ? undefined : { redirect: to.fullPath }
    }
  }

  if (requiresGuest && authStore.isAuthenticated) {
    return '/dashboard/overview'
  }

  return true
})

export default router

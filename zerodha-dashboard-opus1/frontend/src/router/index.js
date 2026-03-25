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
        path: 'fixed-deposits',
        name: 'FixedDeposits',
        component: () => import('@/views/dashboard/FixedDepositsTab.vue')
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

// Navigation guards
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if not authenticated
    next('/login')
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    // Redirect to dashboard if already logged in
    next('/dashboard')
  } else {
    next()
  }
})

export default router

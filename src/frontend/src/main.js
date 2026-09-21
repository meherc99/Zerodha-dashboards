import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import { setUnauthorizedHandler } from './services/api'
import './assets/styles/main.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const authStore = useAuthStore()

const bootstrap = async () => {
  await authStore.initializeAuth()
  app.use(router)
  setUnauthorizedHandler(() => {
    authStore.clearSession()
    if (router.currentRoute.value.path !== '/login') {
      router.replace({
        path: '/login',
        query: { redirect: router.currentRoute.value.fullPath }
      })
    }
  })
  await router.isReady()
  app.mount('#app')
}

bootstrap()

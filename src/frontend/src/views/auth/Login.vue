<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Login to Portfolio Dashboard</h1>
      <p class="subtitle">Track your investments and bank balances</p>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            placeholder="your@email.com"
            required
            autofocus
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="Enter your password"
            required
          />
        </div>

        <button type="submit" :disabled="loading" class="btn-primary">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>

        <p v-if="error" class="error-message" role="alert">{{ error }}</p>
      </form>

      <p class="auth-link">
        Don't have an account?
        <router-link to="/register">Register here</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const { loading, error: authError } = storeToRefs(authStore)

const email = ref('')
const password = ref('')

const error = computed(() => authError.value)

const handleLogin = async () => {
  authStore.clearError()

  try {
    await authStore.login(email.value, password.value)
    const requestedPath = String(route.query.redirect || '')
    const destination = requestedPath.startsWith('/') && !requestedPath.startsWith('//')
      ? requestedPath
      : '/dashboard/overview'
    await router.replace(destination)
  } catch {
    // Error is already set in the store
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  background-color: var(--color-bg);
  background-image:
    radial-gradient(ellipse 70% 55% at 50% 5%, rgba(61, 126, 255, 0.14) 0%, transparent 65%),
    radial-gradient(ellipse 40% 35% at 80% 80%, rgba(167, 139, 250, 0.08) 0%, transparent 60%);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
}

/* top glow line */
.auth-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(61, 126, 255, 0.6), rgba(167, 139, 250, 0.5), transparent);
}

.auth-card h1 {
  margin: 0 0 8px 0;
  font-size: 1.55rem;
  font-weight: 760;
  letter-spacing: -0.03em;
  color: var(--color-text);
}

.subtitle {
  color: var(--color-text-soft);
  margin: 0 0 28px;
  font-size: 0.85rem;
}

.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  margin-bottom: 7px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-text-soft);
  text-transform: uppercase;
}

.form-group input {
  width: 100%;
  padding: 11px 13px;
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  background: var(--color-surface-subtle);
  color: var(--color-text);
  font-size: 0.9rem;
  transition: border-color 0.18s, box-shadow 0.18s;
  box-sizing: border-box;
}

.form-group input::placeholder {
  color: var(--color-text-faint);
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(61, 126, 255, 0.18);
}

.btn-primary {
  width: 100%;
  padding: 12px;
  margin-top: 6px;
  border: 1px solid var(--color-primary);
  border-radius: 10px;
  background: linear-gradient(135deg, #3d7eff, #5b6ef5);
  color: #fff;
  font-size: 0.92rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 0 20px rgba(61, 126, 255, 0.25);
  transition: background 0.18s, box-shadow 0.18s, transform 0.18s;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #5090ff, #7280ff);
  box-shadow: 0 0 30px rgba(61, 126, 255, 0.4);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.error-message {
  margin-top: 14px;
  padding: 10px 13px;
  border: 1px solid rgba(255, 69, 96, 0.3);
  border-left: 3px solid var(--color-negative);
  border-radius: 8px;
  background: var(--color-negative-soft);
  color: var(--color-negative);
  font-size: 0.83rem;
}

.auth-link {
  margin-top: 22px;
  text-align: center;
  font-size: 0.83rem;
  color: var(--color-text-soft);
}

.auth-link a {
  color: var(--color-primary-dark);
  font-weight: 700;
  text-decoration: none;
  transition: color 0.15s;
}

.auth-link a:hover {
  color: var(--color-cyan);
}
</style>

<template>
  <div id="app">
    <header v-if="!isAuthPage" class="app-header">
      <router-link to="/dashboard/overview" class="brand" aria-label="Family Wealth dashboard home">
        <span class="brand-mark" aria-hidden="true">
          <span></span><span></span><span></span>
        </span>
        <span class="brand-copy">
          <strong>Family Wealth</strong>
          <small>Portfolio workspace</small>
        </span>
      </router-link>

      <button
        class="menu-button"
        type="button"
        :aria-expanded="mobileMenuOpen"
        aria-controls="primary-navigation"
        aria-label="Toggle navigation"
        @click="mobileMenuOpen = !mobileMenuOpen"
      >
        <span></span><span></span><span></span>
      </button>

      <nav
        id="primary-navigation"
        class="nav-links"
        :class="{ open: mobileMenuOpen }"
        aria-label="Primary navigation"
      >
        <router-link to="/dashboard/overview" class="nav-link">Portfolio</router-link>
        <router-link to="/accounts" class="nav-link">Family accounts</router-link>
        <span class="privacy-label">
          <span aria-hidden="true">●</span>
          Private workspace
        </span>
        <button
          v-if="authStore.isAuthenticated"
          type="button"
          class="profile-button"
          @click="handleLogout"
        >
          <span class="profile-avatar" aria-hidden="true">{{ userInitials }}</span>
          <span>Sign out</span>
        </button>
      </nav>
    </header>

    <main :class="{ 'main-content': !isAuthPage, 'auth-content': isAuthPage }">
      <router-view />
    </main>

    <div class="notifications" aria-live="polite" aria-atomic="true">
      <div
        v-for="notification in uiStore.notifications"
        :key="notification.id"
        class="notification"
        :class="notification.type"
        role="status"
      >
        {{ notification.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const uiStore = useUiStore()
const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileMenuOpen = ref(false)

const isAuthPage = computed(() => {
  return route.path === '/login' || route.path === '/register'
})

const userInitials = computed(() => {
  const name = authStore.user?.full_name || authStore.user?.email || 'User'
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map(part => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
})

watch(() => route.fullPath, () => {
  mobileMenuOpen.value = false
})

const handleLogout = async () => {
  await authStore.logout()
  await router.push('/login')
}
</script>

<style scoped>
#app {
  min-height: 100vh;
}

/* ─── App Header ─────────────────────────────────── */
.app-header {
  position: sticky;
  z-index: 50;
  top: 0;
  display: flex;
  height: 64px;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--color-border);
  background: rgba(4, 12, 24, 0.88);
  backdrop-filter: blur(20px) saturate(1.6);
  -webkit-backdrop-filter: blur(20px) saturate(1.6);
  box-shadow: 0 1px 0 rgba(255,255,255,0.04), 0 4px 32px rgba(0,0,0,0.5);
}

/* ─── Brand ─────────────────────────────────────── */
.brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  color: var(--color-text);
  text-decoration: none;
}

.brand-mark {
  position: relative;
  display: flex;
  width: 34px;
  height: 34px;
  align-items: flex-end;
  justify-content: center;
  gap: 3px;
  padding: 7px;
  border-radius: 10px;
  background: linear-gradient(145deg, #3d7eff, #a78bfa);
  box-shadow: 0 0 20px rgba(61, 126, 255, 0.38), 0 4px 14px rgba(0, 0, 0, 0.4);
}

.brand-mark span {
  width: 3.5px;
  border-radius: 3px 3px 1px 1px;
  background: rgba(255,255,255,0.92);
}

.brand-mark span:nth-child(1) { height: 7px;  opacity: 0.65; }
.brand-mark span:nth-child(2) { height: 12px; opacity: 0.82; }
.brand-mark span:nth-child(3) { height: 17px; }

.brand-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-copy strong {
  font-size: 0.92rem;
  font-weight: 750;
  letter-spacing: -0.01em;
  background: linear-gradient(90deg, var(--color-text), var(--color-primary-dark));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-copy small {
  margin-top: 2px;
  color: var(--color-text-faint);
  font-size: 0.65rem;
  letter-spacing: 0.04em;
}

/* ─── Navigation ─────────────────────────────────── */
.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-link {
  padding: 7px 12px;
  border-radius: 9px;
  color: var(--color-text-soft);
  font-size: 0.83rem;
  font-weight: 650;
  text-decoration: none;
  transition: color 160ms ease, background 160ms ease;
  letter-spacing: 0.01em;
}

.nav-link:hover {
  background: var(--color-surface-strong);
  color: var(--color-text);
}

.nav-link.router-link-active {
  background: var(--color-primary-soft);
  color: var(--color-primary-dark);
}

/* ─── Privacy label ──────────────────────────────── */
.privacy-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 8px 0 12px;
  color: var(--color-text-faint);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.privacy-label span {
  color: var(--color-positive);
  font-size: 0.5rem;
  text-shadow: 0 0 6px var(--color-positive);
}

/* ─── Profile button ─────────────────────────────── */
.profile-button {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 5px;
  border: 1px solid var(--color-border-strong);
  border-radius: 999px;
  background: var(--color-surface-strong);
  color: var(--color-text-soft);
  font-size: 0.77rem;
  font-weight: 700;
  transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
}

.profile-button:hover {
  border-color: var(--color-border-glow);
  background: var(--color-surface);
  box-shadow: 0 0 12px rgba(61, 126, 255, 0.14);
  color: var(--color-text);
}

.profile-avatar {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #3d7eff, #a78bfa);
  box-shadow: 0 0 10px rgba(61, 126, 255, 0.35);
  color: #fff;
  font-size: 0.64rem;
  font-weight: 800;
}

/* ─── Mobile menu button ─────────────────────────── */
.menu-button {
  display: none;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 4px;
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  background: var(--color-surface-strong);
  transition: border-color 160ms ease;
}

.menu-button:hover {
  border-color: var(--color-border-glow);
}

.menu-button span {
  width: 16px;
  height: 1.5px;
  border-radius: 2px;
  background: var(--color-text-soft);
}

/* ─── Main areas ─────────────────────────────────── */
.main-content {
  min-height: calc(100vh - 64px);
}

.auth-content {
  min-height: 100vh;
}

/* ─── Notifications ──────────────────────────────── */
.notifications {
  position: fixed;
  z-index: 2000;
  top: 76px;
  right: 18px;
  display: flex;
  width: min(380px, calc(100vw - 28px));
  flex-direction: column;
  gap: 8px;
}

.notification {
  padding: 12px 15px;
  border: 1px solid var(--color-border-strong);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: var(--shadow-md);
  color: var(--color-text);
  font-size: 0.83rem;
  font-weight: 650;
  animation: slideIn 220ms ease;
  backdrop-filter: blur(12px);
}

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}

.notification.success {
  border-left: 3px solid var(--color-positive);
  background: var(--color-positive-soft);
  color: var(--color-positive);
}

.notification.error {
  border-left: 3px solid var(--color-negative);
  background: var(--color-negative-soft);
  color: var(--color-negative);
}

.notification.info {
  border-left: 3px solid var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary-dark);
}

/* ─── Responsive ─────────────────────────────────── */
@media (max-width: 768px) {
  .app-header {
    height: 58px;
    padding: 0 14px;
  }

  .menu-button {
    display: inline-flex;
  }

  .nav-links {
    position: absolute;
    top: 57px;
    right: 10px;
    left: 10px;
    display: none;
    align-items: stretch;
    flex-direction: column;
    padding: 8px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: rgba(6, 16, 30, 0.98);
    backdrop-filter: blur(20px);
    box-shadow: var(--shadow-md);
  }

  .nav-links.open {
    display: flex;
  }

  .nav-link {
    padding: 11px 12px;
  }

  .privacy-label {
    margin: 8px 10px 4px;
  }

  .profile-button {
    justify-content: flex-start;
    border-radius: 10px;
  }

  .main-content {
    min-height: calc(100vh - 58px);
  }

  .notifications {
    top: 68px;
    right: 14px;
    left: 14px;
  }
}
</style>



<template>
  <aside class="sidebar" aria-label="Portfolio sections">
    <div class="sidebar-label">Explore</div>
    <nav class="sidebar-nav">
      <router-link
        v-for="item in navigation"
        :key="item.to"
        :to="item.to"
        class="nav-item"
      >
        <span class="icon" aria-hidden="true">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </router-link>
    </nav>
    <div class="sidebar-note">
      <span class="note-icon" aria-hidden="true">✓</span>
      <div>
        <strong>Secure session</strong>
        <span>API requests use your authenticated workspace.</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
const navigation = [
  { to: '/dashboard/overview', label: 'Overview', icon: 'OV' },
  { to: '/dashboard/stocks', label: 'Indian stocks', icon: 'IN' },
  { to: '/dashboard/mutual-funds', label: 'Mutual funds', icon: 'MF' },
  { to: '/dashboard/us-stocks', label: 'US stocks', icon: 'US' },
  { to: '/dashboard/fixed-deposits', label: 'Fixed deposits', icon: 'FD' },
  { to: '/dashboard/bank-balances', label: 'Bank balances', icon: '₹' }
]
</script>

<style scoped>
.sidebar {
  position: sticky;
  top: 68px;
  display: flex;
  width: 228px;
  height: calc(100vh - 68px);
  flex: 0 0 228px;
  flex-direction: column;
  padding: 24px 14px 18px;
  border-right: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.72);
}

.sidebar-label {
  margin: 0 10px 9px;
  color: var(--color-text-faint);
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 43px;
  padding: 8px 10px;
  border-radius: 10px;
  color: var(--color-text-soft);
  text-decoration: none;
  font-size: 0.83rem;
  font-weight: 700;
  transition: color 160ms ease, background 160ms ease;
}

.nav-item:hover {
  background: var(--color-surface-strong);
  color: var(--color-text);
}

.nav-item.router-link-active {
  background: var(--color-primary-soft);
  color: var(--color-primary-dark);
}

.icon {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text-soft);
  font-size: 0.61rem;
  font-weight: 850;
  letter-spacing: -0.02em;
}

.router-link-active .icon {
  border-color: #c5d5ff;
  background: #fff;
  color: var(--color-primary);
}

.sidebar-note {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: auto;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}

.note-icon {
  display: grid;
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-positive-soft);
  color: var(--color-positive);
  font-size: 0.7rem;
  font-weight: 900;
}

.sidebar-note div {
  display: flex;
  flex-direction: column;
}

.sidebar-note strong {
  font-size: 0.72rem;
}

.sidebar-note div span {
  margin-top: 2px;
  color: var(--color-text-faint);
  font-size: 0.62rem;
  line-height: 1.45;
}

@media (max-width: 768px) {
  .sidebar {
    position: sticky;
    z-index: 30;
    top: 62px;
    width: 100%;
    height: auto;
    flex-basis: auto;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    padding: 8px 10px;
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(12px);
  }

  .sidebar-label,
  .sidebar-note {
    display: none;
  }

  .sidebar-nav {
    flex-direction: row;
    gap: 5px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .nav-item {
    flex-shrink: 0;
    min-height: 39px;
    gap: 7px;
    padding: 6px 9px;
    font-size: 0.75rem;
  }

  .icon {
    width: 24px;
    height: 24px;
    flex-basis: 24px;
    border-radius: 7px;
    font-size: 0.55rem;
  }
}
</style>

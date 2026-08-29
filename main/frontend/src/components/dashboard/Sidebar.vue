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
  { to: '/dashboard/eu-stocks', label: 'EU stocks', icon: 'EU' },
  { to: '/dashboard/fixed-deposits', label: 'Fixed deposits', icon: 'FD' },
  { to: '/dashboard/bank-balances', label: 'Bank balances', icon: '₹' }
]
</script>

<style scoped>
.sidebar {
  position: sticky;
  top: 64px;
  display: flex;
  width: 220px;
  height: calc(100vh - 64px);
  flex: 0 0 220px;
  flex-direction: column;
  padding: 22px 12px 16px;
  border-right: 1px solid var(--color-border);
  background: rgba(4, 12, 24, 0.85);
  backdrop-filter: blur(16px);
}

/* ─── Section label ──────────────────────────────── */
.sidebar-label {
  margin: 0 8px 10px;
  color: var(--color-text-faint);
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

/* ─── Nav ────────────────────────────────────────── */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 7px 10px;
  border-radius: 10px;
  color: var(--color-text-soft);
  text-decoration: none;
  font-size: 0.82rem;
  font-weight: 650;
  transition: color 160ms ease, background 160ms ease, box-shadow 160ms ease;
  position: relative;
}

.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2.5px;
  border-radius: 99px;
  background: var(--color-primary);
  opacity: 0;
  transition: opacity 160ms ease;
}

.nav-item:hover {
  background: var(--color-surface-strong);
  color: var(--color-text);
}

.nav-item.router-link-active {
  background: var(--color-primary-soft);
  color: var(--color-primary-dark);
  box-shadow: inset 0 0 16px rgba(61, 126, 255, 0.06);
}

.nav-item.router-link-active::before {
  opacity: 1;
}

/* ─── Icon ───────────────────────────────────────── */
.icon {
  display: grid;
  width: 27px;
  height: 27px;
  flex: 0 0 27px;
  place-items: center;
  border: 1px solid var(--color-border-strong);
  border-radius: 8px;
  background: var(--color-surface-strong);
  color: var(--color-text-faint);
  font-size: 0.58rem;
  font-weight: 850;
  letter-spacing: -0.02em;
  transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
}

.router-link-active .icon {
  border-color: rgba(61, 126, 255, 0.4);
  background: rgba(61, 126, 255, 0.14);
  color: var(--color-primary-dark);
  box-shadow: 0 0 10px rgba(61, 126, 255, 0.15);
}

/* ─── Footer note ────────────────────────────────── */
.sidebar-note {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: auto;
  padding: 11px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: linear-gradient(135deg, var(--color-surface-strong), var(--color-surface));
}

.note-icon {
  display: grid;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-positive-soft);
  color: var(--color-positive);
  font-size: 0.65rem;
  font-weight: 900;
  box-shadow: 0 0 8px rgba(13, 217, 142, 0.25);
}

.sidebar-note div {
  display: flex;
  flex-direction: column;
}

.sidebar-note strong {
  font-size: 0.7rem;
  color: var(--color-text);
}

.sidebar-note div span {
  margin-top: 2px;
  color: var(--color-text-faint);
  font-size: 0.6rem;
  line-height: 1.45;
}

/* ─── Mobile ─────────────────────────────────────── */
@media (max-width: 768px) {
  .sidebar {
    position: sticky;
    z-index: 30;
    top: 58px;
    width: 100%;
    height: auto;
    flex-basis: auto;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    padding: 7px 10px;
    background: rgba(4, 12, 24, 0.97);
    backdrop-filter: blur(20px);
  }

  .sidebar-label,
  .sidebar-note {
    display: none;
  }

  .sidebar-nav {
    flex-direction: row;
    gap: 4px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .nav-item::before { display: none; }

  .nav-item {
    flex-shrink: 0;
    min-height: 38px;
    gap: 6px;
    padding: 6px 9px;
    font-size: 0.74rem;
  }

  .icon {
    width: 23px;
    height: 23px;
    flex-basis: 23px;
    border-radius: 7px;
    font-size: 0.53rem;
  }
}
</style>

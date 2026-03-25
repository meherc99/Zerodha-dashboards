<template>
  <aside class="sidebar">
    <nav class="sidebar-nav">
      <router-link to="/dashboard/overview" class="nav-item">
        <span class="icon">📊</span>
        <span>Overview</span>
      </router-link>
      <router-link to="/dashboard/stocks" class="nav-item">
        <span class="icon">📈</span>
        <span>Stocks</span>
      </router-link>
      <router-link to="/dashboard/mutual-funds" class="nav-item">
        <span class="icon">💰</span>
        <span>Mutual Funds</span>
      </router-link>
      <router-link to="/dashboard/us-stocks" class="nav-item">
        <span class="icon">🇺🇸</span>
        <span>US Stocks</span>
      </router-link>
      <router-link to="/dashboard/fixed-deposits" class="nav-item">
        <span class="icon">🏦</span>
        <span>Fixed Deposits</span>
      </router-link>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 240px;
  background: white;
  border-right: 1px solid #e5e7eb;
  padding: 20px 0;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: #6b7280;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: #f9fafb;
  color: #111827;
}

.nav-item.router-link-active {
  color: #3b82f6;
  background: #eff6ff;
  border-left-color: #3b82f6;
}

.icon {
  font-size: 18px;
}

@media (max-width: 768px) {
  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 10px 0;
  }

  .sidebar-nav {
    display: flex;
    flex-direction: row;
    overflow-x: auto;
  }

  .nav-item {
    flex-shrink: 0;
    border-left: none;
    border-bottom: 3px solid transparent;
  }

  .nav-item.router-link-active {
    border-left-color: transparent;
    border-bottom-color: #3b82f6;
  }
}
</style>

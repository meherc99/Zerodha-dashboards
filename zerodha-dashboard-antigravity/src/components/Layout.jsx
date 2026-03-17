import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Globe, Building2, User } from 'lucide-react';
import { FAMILY_MEMBERS } from '../data/mockData';

const Sidebar = () => {
    return (
        <aside className="sidebar glass-panel" style={{ width: 'var(--sidebar-width)', borderRadius: 0, height: '100vh', borderRight: '1px solid var(--border-light)' }}>
            <div className="sidebar-header" style={{ padding: '2rem 1rem', borderBottom: '1px solid var(--border-light)', marginBottom: '1rem' }}>
                <h2 className="text-gradient flex-center" style={{ gap: '0.5rem' }}>
                    <TrendingUp /> Vault
                </h2>
            </div>

            <nav className="sidebar-nav" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0 1rem' }}>
                <NavLink
                    to="/"
                    end
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    style={{ padding: '0.8rem 1rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)', transition: 'var(--transition-fast)' }}
                >
                    <LayoutDashboard size={20} /> Overview
                </NavLink>
                <NavLink
                    to="/zerodha"
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    style={{ padding: '0.8rem 1rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)', transition: 'var(--transition-fast)' }}
                >
                    <TrendingUp size={20} /> Zerodha
                </NavLink>
                <NavLink
                    to="/us-stocks"
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    style={{ padding: '0.8rem 1rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)', transition: 'var(--transition-fast)' }}
                >
                    <Globe size={20} /> US Stocks
                </NavLink>
                <NavLink
                    to="/fds"
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    style={{ padding: '0.8rem 1rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)', transition: 'var(--transition-fast)' }}
                >
                    <Building2 size={20} /> Fixed Deposits
                </NavLink>
            </nav>

            {/* Embedded Styles specific to nav to keep CSS clean */}
            <style>{`
        .nav-link:hover {
          background: var(--bg-tertiary);
          color: var(--text-primary) !important;
          transform: translateX(4px);
        }
        .nav-link.active {
          background: var(--accent-glow);
          color: var(--accent-primary) !important;
          font-weight: 500;
        }
      `}</style>
        </aside>
    );
};

const Topbar = ({ currentMember, setCurrentMember }) => {
    return (
        <header className="topbar glass-panel flex-between" style={{ height: 'var(--header-height)', borderRadius: 0, borderBottom: '1px solid var(--border-light)', padding: '0 2rem' }}>
            <div>
                <h3 style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</h3>
            </div>

            <div className="member-selector flex-center" style={{ gap: '1rem' }}>
                <User size={20} style={{ color: 'var(--text-secondary)' }} />
                <select
                    value={currentMember}
                    onChange={(e) => setCurrentMember(e.target.value)}
                    style={{
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border-light)',
                        padding: '0.5rem 1rem',
                        borderRadius: '8px',
                        outline: 'none',
                        fontFamily: 'inherit',
                        cursor: 'pointer'
                    }}
                >
                    {FAMILY_MEMBERS.map(member => (
                        <option key={member.id} value={member.id}>
                            {member.name}
                        </option>
                    ))}
                </select>
            </div>
        </header>
    );
};

export const Layout = ({ children, currentMember, setCurrentMember }) => {
    return (
        <div className="app-container">
            <Sidebar />
            <main className="main-content">
                <Topbar currentMember={currentMember} setCurrentMember={setCurrentMember} />
                <div className="page-content animate-fade-in">
                    {children}
                </div>
            </main>
        </div>
    );
};

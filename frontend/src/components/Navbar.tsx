import React from 'react';
import { UserInfo } from '../types';

interface NavbarProps {
  user: UserInfo | null;
  activeTab: 'decks' | 'observatory' | 'templates';
  onSelectTab: (tab: 'decks' | 'observatory' | 'templates') => void;
  onLogout: () => void;
  onOpenQuickstart?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ user, activeTab, onSelectTab, onLogout, onOpenQuickstart }) => (
  <header className="navbar">
    <div className="navbar-brand">
      <span className="brand-logo">🛡️</span>
      <div className="brand-titles">
        <h1>Sentinel Observatory</h1>
        <span className="brand-subtitle">Alan Vo | AI &amp; Machine Learning</span>
      </div>
    </div>
    <nav className="navbar-nav">
      <button className={`nav-link ${activeTab === 'decks' ? 'active' : ''}`} onClick={() => onSelectTab('decks')}>Presentations</button>
      <button className={`nav-link ${activeTab === 'observatory' ? 'active' : ''}`} onClick={() => onSelectTab('observatory')}>Slide Observatory</button>
      <button className={`nav-link ${activeTab === 'templates' ? 'active' : ''}`} onClick={() => onSelectTab('templates')}>Template Studio</button>
      {onOpenQuickstart && (
        <button className="nav-link" onClick={onOpenQuickstart} style={{ color: '#0f3c78', fontWeight: 600 }}>🚀 Quickstart</button>
      )}
    </nav>
    <div className="navbar-user">
      {user ? (
        <div className="user-badge">
          <span>{user.preferred_username || user.email || user.sub}</span>
          {user.demo && <span className="tag demo-tag">Demo Mode</span>}
          <span className="tag role-tag">{user.roles.includes('admin') ? 'Admin' : user.roles.includes('operator') ? 'Operator' : 'Viewer'}</span>
          <button className="btn-secondary btn-sm" onClick={onLogout}>Logout</button>
        </div>
      ) : <span className="tag">Connecting…</span>}
    </div>
  </header>
);

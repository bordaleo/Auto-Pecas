import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import Logo from '../Logo';
import CategoryNav from '../CategoryNav';
import NotificationBell from '../NotificationBell';
import { SidebarToggle } from './SideNav';

export default function Header({ onOpenAuth, onOpenSidebar }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { count, setDrawerOpen } = useCart();
  const [query, setQuery] = useState('');

  const handleSearch = (event) => {
    event.preventDefault();
    const params = new URLSearchParams();
    if (query.trim()) params.set('q', query.trim());
    navigate(`/pecas/?${params.toString()}`);
  };

  const firstName = user?.name?.split(' ')[0] || 'Conta';

  return (
    <header className="site-header">
      <div className="header-main">
        <div className="wrap header-main-inner">
          <div className="header-left">
            <SidebarToggle onClick={onOpenSidebar} />
            <Link to="/" className="header-brand header-brand--mobile" aria-label="Galelugi Peças — Início">
              <Logo light compact />
            </Link>
          </div>

          <form className="header-search" onSubmit={handleSearch}>
            <input
              type="search"
              placeholder="Peça, OEM, SKU, marca ou veículo..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Buscar produtos"
            />
            <button type="submit" className="btn btn-accent btn-search" aria-label="Buscar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
            </button>
          </form>

          <div className="header-actions">
            {user && <NotificationBell />}
            {user ? (
              <Link to="/perfil/" className="header-action">
                <span className="header-action-label">{firstName}</span>
                <span className="header-action-title">Minha conta</span>
              </Link>
            ) : (
              <button type="button" className="header-action" onClick={() => onOpenAuth('login')}>
                <span className="header-action-label">Bem-vindo</span>
                <span className="header-action-title">Entrar</span>
              </button>
            )}

            <button type="button" className="header-cart" onClick={() => setDrawerOpen(true)} aria-label="Carrinho">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <path d="M16 10a4 4 0 0 1-8 0" />
              </svg>
              {count > 0 && <em>{count}</em>}
            </button>
          </div>
        </div>
      </div>

      <CategoryNav />
    </header>
  );
}

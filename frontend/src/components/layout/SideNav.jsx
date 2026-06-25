import { Link, NavLink } from 'react-router-dom';
import { useStore } from '../../context/StoreContext';
import Logo from '../Logo';
import ThemeToggle from '../ThemeToggle';

const SHOP_LINKS = [
  { to: '/pecas/', label: 'Catálogo de peças', icon: 'grid' },
  { to: '/pecas/?featured=1', label: 'Destaques', icon: 'star' },
];

const HELP_LINKS = [
  { to: '/como-funciona/', label: 'Como funciona', icon: 'info' },
  { to: '/faq-compatibilidade/', label: 'Compatibilidade', icon: 'info' },
  { to: '/prazos-entrega/', label: 'Entrega e prazos', icon: 'box' },
  { to: '/trocas-devolucoes/', label: 'Trocas e devoluções', icon: 'store' },
];

const ACCOUNT_LINKS = [
  { to: '/conta/', label: 'Minha conta', icon: 'box' },
  { to: '/vender/', label: 'Minha loja', icon: 'store' },
  { to: '/venda-conosco/', label: 'Venda conosco', icon: 'store', accent: true },
];

function NavIcon({ name }) {
  const icons = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    star: <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />,
    info: <><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" /></>,
    box: <><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></>,
    store: <><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></>,
    chat: <><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" /></>,
  };
  return (
    <svg className="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {icons[name]}
    </svg>
  );
}

export default function SideNav({ open, onClose }) {
  const { whatsappUrl } = useStore();

  return (
    <>
      {open && <button type="button" className="sidebar-overlay" aria-label="Fechar menu" onClick={onClose} />}
      <aside className={`site-sidebar${open ? ' is-open' : ''}`} aria-label="Menu principal">
        <div className="sidebar-top">
          <Link to="/" className="sidebar-brand" onClick={onClose}>
            <Logo light />
          </Link>
        </div>

        <Link to="/pecas/" className="sidebar-cta" onClick={onClose}>
          Explorar catálogo
        </Link>

        <div className="sidebar-group">
          <span className="sidebar-label">Comprar</span>
          <nav className="sidebar-nav">
            {SHOP_LINKS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
                onClick={onClose}
              >
                <NavIcon name={item.icon} />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="sidebar-group">
          <span className="sidebar-label">Conta</span>
          <nav className="sidebar-nav">
            {ACCOUNT_LINKS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/conta/'}
                className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}${item.accent ? ' sidebar-link--accent' : ''}`}
                onClick={onClose}
              >
                <NavIcon name={item.icon} />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="sidebar-group">
          <span className="sidebar-label">Ajuda</span>
          <nav className="sidebar-nav">
            {HELP_LINKS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
                onClick={onClose}
              >
                <NavIcon name={item.icon} />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <a href={whatsappUrl} className="sidebar-link sidebar-link--support" target="_blank" rel="noreferrer" onClick={onClose}>
          <NavIcon name="chat" />
          Suporte WhatsApp
        </a>

        <div className="sidebar-theme">
          <ThemeToggle className="theme-toggle--sidebar" showLabel />
        </div>
      </aside>
    </>
  );
}

export function SidebarToggle({ onClick }) {
  return (
    <button type="button" className="sidebar-toggle" onClick={onClick} aria-label="Abrir menu">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <line x1="4" y1="6" x2="20" y2="6" />
        <line x1="4" y1="12" x2="20" y2="12" />
        <line x1="4" y1="18" x2="20" y2="18" />
      </svg>
    </button>
  );
}

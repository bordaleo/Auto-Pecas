import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../context/StoreContext';

export default function CategoryNav() {
  const { categories } = useStore();
  const [open, setOpen] = useState(false);

  return (
    <nav className="cat-nav" aria-label="Categorias">
      <div className="wrap cat-nav-inner">
        <div className="cat-menu">
          <button
            type="button"
            className="cat-menu-btn"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
            </svg>
            Departamentos
          </button>
          {open && (
            <>
              <div className="cat-menu-overlay" onClick={() => setOpen(false)} />
              <div className="cat-menu-panel">
                <Link to="/pecas/" onClick={() => setOpen(false)}>Todos os produtos</Link>
                {categories.map((cat) => (
                  <Link
                    key={cat.slug}
                    to={`/pecas/?category=${cat.slug}`}
                    onClick={() => setOpen(false)}
                  >
                    <span>{cat.icon || '⚙'}</span>
                    {cat.name}
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="cat-scroll">
          <Link to="/pecas/?featured=1" className="cat-chip cat-chip--accent">Em destaque</Link>
          {categories.map((cat) => (
            <Link key={cat.slug} to={`/pecas/?category=${cat.slug}`} className="cat-chip">
              {cat.name}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

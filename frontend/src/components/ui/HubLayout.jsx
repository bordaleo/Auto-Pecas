import SubTabs from './SubTabs';

/**
 * Layout com navegação lateral — usado em Minha conta e Minha loja.
 */
export default function HubLayout({
  eyebrow,
  title,
  subtitle,
  actions,
  nav,
  activeKey,
  onNavChange,
  subTabs,
  activeSubTab,
  onSubTabChange,
  children,
}) {
  return (
    <div className="hub-layout">
      <header className="hub-layout-head">
        <div>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h1>{title}</h1>
          {subtitle && <p className="hub-layout-lead">{subtitle}</p>}
        </div>
        {actions && <div className="hub-layout-actions">{actions}</div>}
      </header>

      <div className="hub-layout-body">
        <aside className="hub-sidebar" aria-label="Navegação">
          <nav className="hub-nav">
            {nav.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`hub-nav-item${activeKey === item.key ? ' active' : ''}`}
                onClick={() => onNavChange(item.key)}
              >
                <span>{item.label}</span>
                {item.badge > 0 && <em className="hub-nav-badge">{item.badge}</em>}
              </button>
            ))}
          </nav>
        </aside>

        <div className="hub-content">
          {subTabs?.length > 0 && (
            <SubTabs tabs={subTabs} active={activeSubTab} onChange={onSubTabChange} />
          )}
          {children}
        </div>
      </div>
    </div>
  );
}

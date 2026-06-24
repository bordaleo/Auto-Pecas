import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

const NAV_GROUPS = [
  {
    label: 'Operação',
    items: [
      { to: '/painel/visao', label: 'Visão geral' },
      { to: '/painel/pedidos', label: 'Pedidos' },
      { to: '/painel/vendedores', label: 'Vendedores' },
    ],
  },
  {
    label: 'Financeiro',
    items: [
      { to: '/painel/financeiro', label: 'Lucro' },
      { to: '/painel/repasses', label: 'Repasses' },
      { to: '/painel/nfe', label: 'NF-e' },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { to: '/painel/config', label: 'Configurações' },
      { to: '/painel/erros', label: 'Erros' },
    ],
  },
];

export default function PainelLayout() {
  const navigate = useNavigate();

  const logout = async () => {
    await painelApi('/painel/logout', { method: 'POST', body: '{}' });
    navigate('/painel/entrar/');
  };

  return (
    <div className="painel-shell">
      <aside className="painel-sidebar">
        <div className="painel-brand">
          <strong>Galelugi</strong>
          <span>Painel operacional</span>
        </div>
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="painel-nav-group">
            <span className="painel-nav-label">{group.label}</span>
            <nav>
              {group.items.map((tab) => (
                <NavLink key={tab.to} to={tab.to} className={({ isActive }) => `painel-nav${isActive ? ' active' : ''}`}>
                  {tab.label}
                </NavLink>
              ))}
            </nav>
          </div>
        ))}
        <button type="button" className="painel-logout" onClick={logout}>Sair</button>
      </aside>
      <main className="painel-main">
        <Outlet />
      </main>
    </div>
  );
}

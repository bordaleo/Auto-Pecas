import { NavLink, Outlet, useOutletContext } from 'react-router-dom';
import PageSeo from '../../components/PageSeo';
import { getToken } from '../../api/client';

const NAV = [
  { to: '/conta/perfil', label: 'Dados pessoais', end: true },
  { to: '/conta/pedidos', label: 'Meus pedidos' },
  { to: '/conta/solicitacoes', label: 'Pedidos de peça' },
];

export default function AccountLayout() {
  const { openAuth } = useOutletContext() || {};

  if (!getToken()) {
    return (
      <div className="wrap internal-page">
        <div className="internal-page-card account-gate">
          <span className="eyebrow">Minha conta</span>
          <h1>Entre para acessar</h1>
          <p>Pedidos, solicitações de peça e dados de entrega ficam aqui.</p>
          <button type="button" className="btn btn-accent" onClick={() => openAuth?.('login')}>
            Entrar ou criar conta
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageSeo title="Minha conta | Galelugi Peças" description="Pedidos, solicitações e dados pessoais." />
      <div className="wrap account-hub">
        <header className="account-hub-head">
          <span className="eyebrow">Minha conta</span>
          <h1>Central do cliente</h1>
          <p>Pedidos, peças solicitadas e endereço de entrega em um só lugar.</p>
        </header>

        <div className="account-hub-body">
          <aside className="account-hub-nav" aria-label="Seções da conta">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `account-hub-link${isActive ? ' active' : ''}`}
              >
                {item.label}
              </NavLink>
            ))}
            <NavLink to="/vender/" className="account-hub-link account-hub-link--accent">
              Minha loja (vendedor)
            </NavLink>
          </aside>
          <div className="account-hub-content">
            <Outlet context={{ accountEmbedded: true, openAuth }} />
          </div>
        </div>
      </div>
    </>
  );
}

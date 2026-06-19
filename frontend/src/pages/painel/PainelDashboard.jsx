import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatCurrency, painelApi } from '../../api/client';

function usePainelAuth() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    painelApi('/painel/session')
      .then((data) => {
        if (!data.authenticated) navigate('/painel/entrar/', { replace: true });
        else setReady(true);
      })
      .catch(() => navigate('/painel/entrar/', { replace: true }));
  }, [navigate]);

  return ready;
}

export function PainelDashboard() {
  const ready = usePainelAuth();
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!ready) return;
    painelApi('/painel/dashboard?page=visao&days=14').then(setData).catch(() => {});
  }, [ready]);

  if (!ready || !data) return <p>Carregando...</p>;
  const t = data.totals || {};

  return (
    <div>
      <h1>Visão geral</h1>
      <div className="painel-stats">
        <article><strong>{formatCurrency(t.revenue || 0)}</strong><span>Receita (14d)</span></article>
        <article><strong>{t.orders_approved || 0}</strong><span>Pedidos pagos</span></article>
        <article><strong>{t.products || 0}</strong><span>Peças ativas</span></article>
        <article><strong>{t.users || 0}</strong><span>Usuários</span></article>
      </div>
      <h2>Pedidos recentes</h2>
      <div className="painel-table">
        {(data.recent_orders || []).map((o) => (
          <div key={o.id} className="painel-row">
            <span>#{o.id}</span>
            <span>{o.customer_name || o.user__email}</span>
            <span>{formatCurrency(o.amount)}</span>
            <span>{o.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default PainelDashboard;

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
    Promise.all([
      painelApi('/painel/dashboard?page=visao&days=14'),
      painelApi('/painel/finance?days=30'),
    ]).then(([dash, finance]) => setData({ ...dash, finance })).catch(() => {});
  }, [ready]);

  if (!ready || !data) return <p>Carregando...</p>;
  const t = data.totals || {};
  const f = data.finance || {};

  return (
    <div>
      <h1>Visão geral</h1>
      <div className="painel-stats">
        <article><strong>{formatCurrency(t.revenue || 0)}</strong><span>Receita (14d)</span></article>
        <article><strong>{formatCurrency(f.platform_profit_estimate || 0)}</strong><span>Lucro plataforma (30d)</span></article>
        <article><strong>{formatCurrency(f.platform_commission || 0)}</strong><span>Comissões (30d)</span></article>
        <article><strong>{formatCurrency(f.pending_payouts || 0)}</strong><span>Repasses pendentes</span></article>
        <article><strong>{t.orders_approved || 0}</strong><span>Pedidos pagos</span></article>
        <article><strong>{t.products || 0}</strong><span>Peças ativas</span></article>
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

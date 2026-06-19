import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatCurrency, painelApi } from '../../api/client';

function usePainelAuth() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/', { replace: true }); else setReady(true); })
      .catch(() => navigate('/painel/entrar/', { replace: true }));
  }, [navigate]);
  return ready;
}

export default function PainelFinance() {
  const ready = usePainelAuth();
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!ready) return;
    painelApi('/painel/finance?days=30').then(setData).catch(() => {});
  }, [ready]);

  if (!ready || !data) return <p>Carregando...</p>;

  return (
    <div>
      <h1>Lucro da plataforma</h1>
      <p className="painel-sub">Últimos {data.period_days} dias — comissões, margem própria e repasses.</p>
      <div className="painel-stats">
        <article><strong>{formatCurrency(data.platform_profit_estimate)}</strong><span>Lucro estimado</span></article>
        <article><strong>{formatCurrency(data.platform_commission)}</strong><span>Comissões marketplace</span></article>
        <article><strong>{formatCurrency(data.own_store_margin)}</strong><span>Margem loja própria</span></article>
        <article><strong>{formatCurrency(data.shipping_revenue)}</strong><span>Receita de frete</span></article>
        <article><strong>{formatCurrency(data.pending_payouts)}</strong><span>Repasses pendentes</span></article>
        <article><strong>{formatCurrency(data.total_paid_to_sellers)}</strong><span>Já pago a vendedores</span></article>
      </div>

      <h2>Detalhamento</h2>
      <div className="painel-table">
        <div className="painel-row painel-row-head">
          <span>Métrica</span><span>Valor</span>
        </div>
        <div className="painel-row"><span>Receita bruta (pedidos)</span><span>{formatCurrency(data.gross_revenue)}</span></div>
        <div className="painel-row"><span>Vendas loja própria</span><span>{formatCurrency(data.own_store_revenue)}</span></div>
        <div className="painel-row"><span>Custo loja própria</span><span>{formatCurrency(data.own_store_cost)}</span></div>
        <div className="painel-row"><span>Repasse acumulado vendedores</span><span>{formatCurrency(data.seller_earnings_accrued)}</span></div>
        <div className="painel-row"><span>Saldo vendedores (estimado)</span><span>{formatCurrency(data.seller_balance_outstanding)}</span></div>
      </div>
    </div>
  );
}

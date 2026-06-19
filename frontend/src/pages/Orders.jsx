import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken } from '../api/client';
import PageSeo from '../components/PageSeo';

const TRACK_STEPS = [
  { key: 'pending', label: 'Aguardando envio' },
  { key: 'processing', label: 'Em separação' },
  { key: 'shipped', label: 'Enviado' },
  { key: 'delivered', label: 'Entregue' },
];

function TrackingTimeline({ order }) {
  if (order.status !== 'approved' || order.delivery_method === 'pickup') return null;
  const current = order.shipping_status || 'pending';
  const idx = TRACK_STEPS.findIndex((s) => s.key === current);

  return (
    <div className="order-tracking">
      <h4>Rastreamento</h4>
      <div className="tracking-steps">
        {TRACK_STEPS.map((step, i) => (
          <div key={step.key} className={`tracking-step${i <= idx ? ' done' : ''}${i === idx ? ' current' : ''}`}>
            <span className="tracking-dot" />
            <span>{step.label}</span>
          </div>
        ))}
      </div>
      {order.tracking_code && (
        <div className="tracking-code">
          <span>{order.carrier || 'Transportadora'}: <strong>{order.tracking_code}</strong></span>
          {order.tracking_url && (
            <a href={order.tracking_url} target="_blank" rel="noreferrer">Rastrear pacote</a>
          )}
        </div>
      )}
      {order.shipped_at && (
        <p className="tracking-meta">Enviado em {new Date(order.shipped_at).toLocaleString('pt-BR')}</p>
      )}
    </div>
  );
}

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const { openAuth } = useOutletContext();

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api('/shop/orders/')
      .then(setOrders)
      .catch(() => setOrders([]))
      .finally(() => setLoading(false));
  }, []);

  if (!getToken()) {
    return (
      <div className="wrap internal-page orders-page">
        <div className="internal-page-card">
          <p className="state-empty">
            Faça login para ver seus pedidos.{' '}
            <button type="button" className="btn btn-accent" onClick={() => openAuth('login')}>Entrar</button>
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageSeo title="Meus pedidos | Galelugi Peças" description="Acompanhe suas compras e rastreamento de entrega." />
      <div className="wrap internal-page orders-page">
        <header className="internal-page-head">
          <h1>Suas compras</h1>
          <p>Histórico de pedidos e rastreamento de envio.</p>
        </header>

        {loading && <div className="internal-page-card"><p>Carregando...</p></div>}
        {!loading && orders.length === 0 && (
          <div className="internal-page-card">
            <p className="state-empty">Nenhum pedido. <Link to="/pecas/">Comprar peças</Link></p>
          </div>
        )}
        {orders.map((order) => (
          <article key={order.id} className="internal-page-card order-card">
            <div className="order-card-head">
              <strong>Pedido #{order.id}</strong>
              <span className={`order-status order-status--${order.status}`}>
                {order.status_display}
              </span>
            </div>
            <div className="order-card-meta">
              {new Date(order.created_at).toLocaleString('pt-BR')} · {formatCurrency(order.amount)}
              {order.discount_amount > 0 && ` · Cupom ${order.coupon_code} (-${formatCurrency(order.discount_amount)})`}
            </div>
            <div className="order-card-meta">
              {order.delivery_method_display || 'Entrega'}
              {order.shipping_fee > 0 ? ` · Frete ${formatCurrency(order.shipping_fee)}` : ' · Frete grátis'}
            </div>
            <TrackingTimeline order={order} />
            <div className="order-items">
              {(order.items || []).map((item) => (
                <div key={item.id} className="order-item-row">
                  {item.quantity}x {item.product_name} — {formatCurrency(item.subtotal)}
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

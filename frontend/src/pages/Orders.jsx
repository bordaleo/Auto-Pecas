import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken } from '../api/client';
import PageSeo from '../components/PageSeo';
import { useToast } from '../context/ToastContext';

const TRACK_STEPS = [
  { key: 'pending', label: 'Aguardando envio' },
  { key: 'processing', label: 'Em separação' },
  { key: 'shipped', label: 'Enviado' },
  { key: 'delivered', label: 'Entregue' },
];

function groupOrders(orders) {
  const map = new Map();
  orders.forEach((order) => {
    const key = order.order_group_id ? `g-${order.order_group_id}` : `o-${order.id}`;
    if (!map.has(key)) {
      map.set(key, {
        key,
        groupId: order.order_group_id,
        created_at: order.created_at,
        orders: [],
        total: 0,
      });
    }
    const group = map.get(key);
    group.orders.push(order);
    group.total += parseFloat(order.amount || 0);
  });
  return Array.from(map.values());
}

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
  const [returns, setReturns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [returnForm, setReturnForm] = useState({ order_item_id: '', reason: '', description: '' });
  const [invoiceForm, setInvoiceForm] = useState({ order_id: '', cnpj: '', company_name: '', company_email: '' });
  const { openAuth } = useOutletContext();
  const { showToast } = useToast();

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    Promise.all([api('/shop/orders/'), api('/returns/')])
      .then(([orderList, returnList]) => {
        setOrders(orderList);
        setReturns(returnList);
      })
      .catch(() => {
        setOrders([]);
        setReturns([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const requestInvoice = async (e) => {
    e.preventDefault();
    try {
      await api('/invoices/', {
        method: 'POST',
        body: JSON.stringify({
          order_id: parseInt(invoiceForm.order_id, 10),
          cnpj: invoiceForm.cnpj,
          company_name: invoiceForm.company_name,
          company_email: invoiceForm.company_email || undefined,
        }),
      });
      showToast('NF-e solicitada! Você será notificado quando emitida.');
      setInvoiceForm({ order_id: '', cnpj: '', company_name: '', company_email: '' });
    } catch (err) {
      showToast(err.message);
    }
  };

  const requestReturn = async (e) => {
    e.preventDefault();
    try {
      await api('/returns/', {
        method: 'POST',
        body: JSON.stringify({
          order_item_id: parseInt(returnForm.order_item_id, 10),
          reason: returnForm.reason,
          description: returnForm.description,
        }),
      });
      showToast('Devolução solicitada');
      const returnList = await api('/returns/');
      setReturns(returnList);
      setReturnForm({ order_item_id: '', reason: '', description: '' });
    } catch (err) {
      showToast(err.message);
    }
  };

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
        {groupOrders(orders).map((group) => (
          <article key={group.key} className="internal-page-card order-card">
            <div className="order-card-head">
              <strong>
                {group.groupId ? `Compra #${group.groupId}` : `Pedido #${group.orders[0].id}`}
                {group.orders.length > 1 && ` · ${group.orders.length} lojas`}
              </strong>
              <span className={`order-status order-status--${group.orders[0].status}`}>
                {group.orders[0].status_display}
              </span>
            </div>
            <div className="order-card-meta">
              {new Date(group.created_at).toLocaleString('pt-BR')} · Total {formatCurrency(group.total)}
            </div>

            {group.orders.map((order) => (
              <div key={order.id} className="order-sub-block">
                <div className="order-card-meta order-sub-head">
                  <strong>{order.store_label || order.fulfillment_seller_name || 'Galelugi Peças'}</strong>
                  {' · '}
                  Pedido #{order.id} · {formatCurrency(order.amount)}
                  {order.discount_amount > 0 && ` · Cupom ${order.coupon_code}`}
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
                      {order.status === 'approved' && (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ marginLeft: '0.5rem' }}
                          onClick={() => setReturnForm({ ...returnForm, order_item_id: String(item.id) })}
                        >
                          Devolução
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                {order.status === 'approved' && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ marginTop: '0.5rem' }}
                    onClick={() => setInvoiceForm({ ...invoiceForm, order_id: String(order.id) })}
                  >
                    Solicitar NF-e
                  </button>
                )}
              </div>
            ))}
          </article>
        ))}

        {invoiceForm.order_id && (
          <form className="internal-page-card" onSubmit={requestInvoice}>
            <h3>Solicitar NF-e — pedido #{invoiceForm.order_id}</h3>
            <div className="form-group">
              <label>CNPJ</label>
              <input value={invoiceForm.cnpj} onChange={(e) => setInvoiceForm({ ...invoiceForm, cnpj: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Razão social</label>
              <input value={invoiceForm.company_name} onChange={(e) => setInvoiceForm({ ...invoiceForm, company_name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>E-mail fiscal</label>
              <input type="email" value={invoiceForm.company_email} onChange={(e) => setInvoiceForm({ ...invoiceForm, company_email: e.target.value })} />
            </div>
            <button type="submit" className="btn btn-accent">Solicitar nota fiscal</button>
            <button type="button" className="btn btn-secondary" style={{ marginLeft: '0.5rem' }} onClick={() => setInvoiceForm({ order_id: '', cnpj: '', company_name: '', company_email: '' })}>Cancelar</button>
          </form>
        )}

        {returnForm.order_item_id && (
          <form className="internal-page-card" onSubmit={requestReturn}>
            <h3>Solicitar devolução — item #{returnForm.order_item_id}</h3>
            <div className="form-group">
              <label>Motivo</label>
              <select value={returnForm.reason} onChange={(e) => setReturnForm({ ...returnForm, reason: e.target.value })} required>
                <option value="">Selecione</option>
                <option value="defeito">Peça com defeito</option>
                <option value="incompativel">Incompatível com veículo</option>
                <option value="divergente">Diferente do anunciado</option>
                <option value="arrependimento">Arrependimento (7 dias)</option>
              </select>
            </div>
            <div className="form-group">
              <label>Descrição</label>
              <textarea rows={3} value={returnForm.description} onChange={(e) => setReturnForm({ ...returnForm, description: e.target.value })} />
            </div>
            <button type="submit" className="btn btn-accent">Enviar solicitação</button>
            <button type="button" className="btn btn-secondary" style={{ marginLeft: '0.5rem' }} onClick={() => setReturnForm({ order_item_id: '', reason: '', description: '' })}>Cancelar</button>
          </form>
        )}

        {returns.length > 0 && (
          <section className="internal-page-card">
            <h3>Minhas devoluções</h3>
            {returns.map((r) => (
              <div key={r.id} className="order-item-row">
                Pedido #{r.order_id} — {r.product_name}: <strong>{r.status_display}</strong>
              </div>
            ))}
          </section>
        )}
      </div>
    </>
  );
}

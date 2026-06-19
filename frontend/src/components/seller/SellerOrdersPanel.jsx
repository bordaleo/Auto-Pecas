import { useEffect, useState } from 'react';
import { api, formatCurrency } from '../../api/client';
import { useToast } from '../../context/ToastContext';

const SHIPPING_STATUSES = [
  { value: 'pending', label: 'Aguardando envio' },
  { value: 'processing', label: 'Em separação' },
  { value: 'shipped', label: 'Enviado' },
  { value: 'delivered', label: 'Entregue' },
];

export default function SellerOrdersPanel() {
  const { showToast } = useToast();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    api('/seller/orders/')
      .then(setOrders)
      .catch(() => setOrders([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const updateShipping = async (itemId, payload) => {
    try {
      await api(`/seller/orders/${itemId}/`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      showToast('Envio atualizado');
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  if (loading) return <p className="state-empty">Carregando pedidos...</p>;
  if (!orders.length) return <p className="state-empty">Nenhum pedido pago ainda.</p>;

  return (
    <div className="seller-orders-panel">
      {orders.map((item) => (
        <article key={item.id} className="seller-order-card">
          <div className="seller-order-head">
            <strong>Pedido #{item.order_id}</strong>
            <span>{new Date(item.order_created_at).toLocaleDateString('pt-BR')}</span>
          </div>
          <p><strong>{item.quantity}x {item.product_name}</strong> — {formatCurrency(item.subtotal)}</p>
          <p className="seller-product-meta">Você recebe: {formatCurrency(item.seller_earning)}</p>
          <p className="seller-product-meta">
            Cliente: {item.customer_name} · {item.shipping_city}/{item.shipping_state}
          </p>
          <p className="seller-product-meta">{item.shipping_address} — CEP {item.shipping_zip}</p>

          <div className="form-row-2" style={{ marginTop: '0.75rem' }}>
            <select
              value={item.item_shipping_status}
              onChange={(e) => updateShipping(item.id, { item_shipping_status: e.target.value })}
            >
              {SHIPPING_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <input
              placeholder="Transportadora"
              defaultValue={item.item_carrier}
              onBlur={(e) => {
                if (e.target.value !== item.item_carrier) {
                  updateShipping(item.id, { item_carrier: e.target.value });
                }
              }}
            />
          </div>
          <div className="form-row-2" style={{ marginTop: '0.5rem' }}>
            <input
              placeholder="Código de rastreio"
              defaultValue={item.item_tracking_code}
              onBlur={(e) => {
                if (e.target.value !== item.item_tracking_code) {
                  updateShipping(item.id, { item_tracking_code: e.target.value });
                }
              }}
            />
            {item.tracking_url && (
              <a href={item.tracking_url} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
                Rastrear
              </a>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

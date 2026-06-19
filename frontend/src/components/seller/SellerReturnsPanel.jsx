import { useEffect, useState } from 'react';
import { api, formatCurrency } from '../../api/client';
import { useToast } from '../../context/ToastContext';

export default function SellerReturnsPanel() {
  const { showToast } = useToast();
  const [returns, setReturns] = useState([]);

  const load = () => api('/seller/returns/').then(setReturns).catch(() => setReturns([]));

  useEffect(() => { load(); }, []);

  const updateStatus = async (id, status, seller_response = '') => {
    try {
      await api(`/returns/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ status, seller_response }),
      });
      showToast('Devolução atualizada');
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  if (!returns.length) return <p className="state-empty">Nenhuma devolução pendente.</p>;

  return (
    <div className="seller-returns-panel">
      {returns.map((r) => (
        <article key={r.id} className="seller-order-card">
          <strong>Pedido #{r.order_id} — {r.product_name}</strong>
          <p>Motivo: {r.reason}</p>
          {r.description && <p>{r.description}</p>}
          <p className="seller-product-meta">Status: {r.status_display}</p>
          {r.status === 'requested' && (
            <div className="seller-product-actions">
              <button type="button" className="btn btn-accent btn-sm" onClick={() => updateStatus(r.id, 'approved', 'Devolução aprovada.')}>
                Aprovar
              </button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => updateStatus(r.id, 'rejected', 'Devolução não aprovada.')}>
                Rejeitar
              </button>
            </div>
          )}
          {r.refund_amount && <p>Reembolso: {formatCurrency(r.refund_amount)}</p>}
        </article>
      ))}
    </div>
  );
}

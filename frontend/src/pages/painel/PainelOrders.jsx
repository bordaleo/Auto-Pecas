import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatCurrency, painelApi } from '../../api/client';

export default function PainelOrders() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [choices, setChoices] = useState([]);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ tracking_code: '', carrier: '', shipping_status: 'pending' });

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); })
      .catch(() => navigate('/painel/entrar/'));
    painelApi('/painel/dashboard?page=pedidos&days=30')
      .then((data) => {
        setOrders(data.orders || []);
        setChoices(data.shipping_status_choices || []);
      })
      .catch(() => {});
  }, [navigate]);

  const openEdit = (order) => {
    setEditing(order.id);
    setForm({
      tracking_code: order.tracking_code || '',
      carrier: order.carrier || '',
      shipping_status: order.shipping_status || 'pending',
    });
  };

  const save = async () => {
    try {
      await painelApi(`/painel/orders/${editing}`, {
        method: 'PATCH',
        body: JSON.stringify(form),
      });
      const data = await painelApi('/painel/dashboard?page=pedidos&days=30');
      setOrders(data.orders || []);
      setEditing(null);
    } catch {
      /* ignore */
    }
  };

  return (
    <div>
      <h1>Pedidos e rastreio</h1>
      <div className="painel-table painel-table--orders">
        {orders.map((o) => (
          <div key={o.id} className="painel-order-card">
            <div className="painel-row">
              <strong>#{o.id}</strong>
              <span>{o.customer_name}</span>
              <span>{formatCurrency(o.amount)}</span>
              <span className={`status-${o.status}`}>{o.status}</span>
            </div>
            <div className="painel-row-meta">
              Envio: {o.shipping_status || 'pending'}
              {o.tracking_code && ` · ${o.carrier} ${o.tracking_code}`}
            </div>
            {editing === o.id ? (
              <div className="painel-edit-form">
                <input placeholder="Código rastreio" value={form.tracking_code} onChange={(e) => setForm({ ...form, tracking_code: e.target.value })} />
                <input placeholder="Transportadora" value={form.carrier} onChange={(e) => setForm({ ...form, carrier: e.target.value })} />
                <select value={form.shipping_status} onChange={(e) => setForm({ ...form, shipping_status: e.target.value })}>
                  {choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <button type="button" className="btn btn-accent btn-sm" onClick={save}>Salvar</button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditing(null)}>Cancelar</button>
              </div>
            ) : (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => openEdit(o)}>Atualizar rastreio</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken } from '../api/client';
import FormCard, { FormField } from './ui/FormCard';
import PageLoader from './ui/PageLoader';
import { useToast } from '../context/ToastContext';

const REASONS = [
  { value: 'defeito', label: 'Peça com defeito' },
  { value: 'incompativel', label: 'Incompatível com meu veículo' },
  { value: 'divergente', label: 'Diferente do anunciado' },
  { value: 'arrependimento', label: 'Arrependimento (7 dias)' },
];

function groupOrders(orders) {
  const map = new Map();
  orders.forEach((order) => {
    const key = order.order_group_id || `single-${order.id}`;
    if (!map.has(key)) {
      map.set(key, { key, groupId: order.order_group_id, orders: [] });
    }
    map.get(key).orders.push(order);
  });
  return [...map.values()];
}

export default function ReturnRequestPanel({ compact = false }) {
  const { openAuth } = useOutletContext() || {};
  const { showToast } = useToast();
  const [orders, setOrders] = useState([]);
  const [returns, setReturns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ order_item_id: '', reason: '', description: '' });

  const load = () => {
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
  };

  useEffect(() => { load(); }, []);

  const returnableItems = useMemo(() => {
    const openItemIds = new Set(returns
      .filter((r) => !['rejected', 'closed', 'refunded'].includes(r.status))
      .map((r) => r.order_item_id));
    const items = [];
    orders.forEach((order) => {
      if (order.status !== 'approved') return;
      (order.items || []).forEach((item) => {
        if (openItemIds.has(item.id)) return;
        items.push({
          id: item.id,
          label: `${item.product_name} · Pedido #${order.id} · ${formatCurrency(item.subtotal || item.price)}`,
          orderId: order.id,
        });
      });
    });
    return items;
  }, [orders, returns]);

  const submit = async (event) => {
    event.preventDefault();
    try {
      await api('/returns/', {
        method: 'POST',
        body: JSON.stringify({
          order_item_id: parseInt(form.order_item_id, 10),
          reason: form.reason,
          description: form.description,
        }),
      });
      showToast('Solicitação enviada! Acompanhe o status abaixo.');
      setForm({ order_item_id: '', reason: '', description: '' });
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  if (!getToken()) {
    return (
      <FormCard title="Solicitar troca ou devolução" hint="Faça login para abrir uma solicitação pelo site.">
        <p className="form-hint" style={{ marginBottom: '1rem' }}>
          Você também pode falar com o suporte pelo WhatsApp, mas pelo site o acompanhamento fica centralizado em Meus pedidos.
        </p>
        <button type="button" className="btn btn-accent" onClick={() => openAuth?.('login')}>
          Entrar para solicitar
        </button>
        {' '}
        <Link to="/conta/pedidos/" className="btn btn-secondary">Ir para Meus pedidos</Link>
      </FormCard>
    );
  }

  if (loading) return <PageLoader label="Carregando pedidos..." />;

  return (
    <div className="return-request-panel">
      <FormCard
        title="Solicitar troca ou devolução"
        hint="Selecione o item da compra, informe o motivo e envie. O vendedor analisa em até 2 dias úteis."
      >
        {returnableItems.length === 0 ? (
          <p className="form-hint">
            Nenhum item elegível no momento. Só é possível solicitar para pedidos <strong>pagos</strong> sem devolução aberta.
            {' '}
            <Link to="/conta/pedidos/">Ver meus pedidos</Link>
          </p>
        ) : (
          <form onSubmit={submit}>
            <FormField label="Item da compra" hint="Pedidos aprovados e ainda sem devolução aberta.">
              <select
                value={form.order_item_id}
                onChange={(e) => setForm({ ...form, order_item_id: e.target.value })}
                required
              >
                <option value="">Selecione a peça</option>
                {returnableItems.map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Motivo">
              <select
                value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
                required
              >
                <option value="">Selecione</option>
                {REASONS.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Descreva o problema" hint="Fotos podem ser enviadas pelo WhatsApp após abrir a solicitação.">
              <textarea
                rows={3}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Ex.: peça veio riscada / código OEM não bate com meu carro..."
              />
            </FormField>
            <button type="submit" className="btn btn-accent">Enviar solicitação</button>
          </form>
        )}
      </FormCard>

      {returns.length > 0 && (
        <FormCard title="Suas solicitações" className={compact ? '' : 'return-list-card'}>
          <ul className="return-status-list">
            {returns.map((r) => (
              <li key={r.id}>
                <strong>{r.product_name || `Item #${r.order_item_id}`}</strong>
                <span>Pedido #{r.order_id}</span>
                <em className={`status-pill status-${r.status}`}>{r.status_display}</em>
              </li>
            ))}
          </ul>
          <Link to="/conta/pedidos/" className="btn btn-secondary btn-sm" style={{ marginTop: '0.75rem' }}>
            Gerenciar em Meus pedidos
          </Link>
        </FormCard>
      )}

      {!compact && groupOrders(orders).length > 0 && (
        <p className="form-hint" style={{ marginTop: '1rem' }}>
          Dúvidas? Abra a solicitação acima ou fale com o suporte pelo WhatsApp informando o número do pedido.
        </p>
      )}
    </div>
  );
}

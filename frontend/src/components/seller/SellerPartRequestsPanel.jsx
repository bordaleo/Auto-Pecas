import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, formatCurrency } from '../../api/client';
import { useToast } from '../../context/ToastContext';

const QUOTE_FORM_EMPTY = {
  message: '',
  quote_price: '',
  quote_condition: 'used',
  quote_delivery_days: '',
  quote_product_id: '',
  quote_notes: '',
};

function formatVehicle(req) {
  const parts = [req.vehicle_brand, req.vehicle_model, req.vehicle_year].filter(Boolean);
  return parts.length ? parts.join(' · ') : null;
}

export default function SellerPartRequestsPanel() {
  const { showToast } = useToast();
  const [requests, setRequests] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [myProducts, setMyProducts] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [quoteForm, setQuoteForm] = useState(QUOTE_FORM_EMPTY);
  const [respondingId, setRespondingId] = useState(null);

  const loadRequests = () => api('/seller/part-requests/').then(setRequests).catch(() => setRequests([]));
  const loadConversations = () => api('/part-requests/conversations/').then(setConversations).catch(() => setConversations([]));

  useEffect(() => {
    loadRequests();
    loadConversations();
    api('/seller/products/').then(setMyProducts).catch(() => setMyProducts([]));
  }, []);

  const openChat = async (convId) => {
    setActiveConvId(convId);
    const msgs = await api(`/part-requests/chat/${convId}/messages/`);
    setMessages(msgs);
    loadConversations();
  };

  const respond = async (requestId) => {
    try {
      const payload = {
        message: quoteForm.message.trim() || undefined,
        quote_notes: quoteForm.quote_notes.trim() || undefined,
      };
      if (quoteForm.quote_price) payload.quote_price = parseFloat(quoteForm.quote_price);
      if (quoteForm.quote_condition) payload.quote_condition = quoteForm.quote_condition;
      if (quoteForm.quote_delivery_days) payload.quote_delivery_days = parseInt(quoteForm.quote_delivery_days, 10);
      if (quoteForm.quote_product_id) payload.quote_product_id = parseInt(quoteForm.quote_product_id, 10);

      const conv = await api(`/part-requests/${requestId}/respond/`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      showToast('Orçamento enviado ao solicitante!');
      setRespondingId(null);
      setQuoteForm(QUOTE_FORM_EMPTY);
      loadRequests();
      loadConversations();
      openChat(conv.id);
    } catch (err) {
      showToast(err.message);
    }
  };

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim() || !activeConvId) return;
    try {
      await api(`/part-requests/chat/${activeConvId}/messages/`, {
        method: 'POST',
        body: JSON.stringify({ body: text.trim() }),
      });
      setText('');
      openChat(activeConvId);
    } catch (err) {
      showToast(err.message);
    }
  };

  const activeConv = conversations.find((c) => c.id === activeConvId);

  return (
    <div className="part-request-hub">
      <div className="part-request-list">
        <h3>Pedidos abertos ({requests.length})</h3>
        <p className="form-hint">Ordenados por compatibilidade com seu estoque e proximidade do CEP.</p>
        {!requests.length && (
          <p className="state-empty">Nenhum pedido de peça aberto no momento.</p>
        )}
        {requests.map((req) => (
          <article key={req.id} className="part-request-card">
            <div className="part-request-card-head">
              <p className="part-request-desc">{req.description}</p>
              {req.match_score >= 20 && (
                <span className="match-badge">{req.match_score}% match</span>
              )}
            </div>
            {formatVehicle(req) && (
              <p className="part-request-vehicle">{formatVehicle(req)}</p>
            )}
            <p className="seller-product-meta">
              {req.requester_name}
              {req.show_phone && req.contact_phone && (
                <> · <a href={`tel:${req.contact_phone}`}>{req.contact_phone}</a></>
              )}
              {req.proximity_score > 0 && <> · CEP próximo ({req.proximity_score}%)</>}
              {' · '}{req.response_count} resposta(s)
              {req.days_until_expiry != null && <> · expira em {req.days_until_expiry}d</>}
            </p>
            {respondingId === req.id ? (
              <div className="part-request-respond-form">
                <div className="form-row">
                  <div className="form-group">
                    <label>Preço (R$)</label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={quoteForm.quote_price}
                      onChange={(e) => setQuoteForm({ ...quoteForm, quote_price: e.target.value })}
                      placeholder="450.00"
                    />
                  </div>
                  <div className="form-group">
                    <label>Condição</label>
                    <select
                      value={quoteForm.quote_condition}
                      onChange={(e) => setQuoteForm({ ...quoteForm, quote_condition: e.target.value })}
                    >
                      <option value="new">Nova</option>
                      <option value="used">Usada</option>
                      <option value="reconditioned">Recondicionada</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Prazo (dias úteis)</label>
                    <input
                      type="number"
                      min="1"
                      value={quoteForm.quote_delivery_days}
                      onChange={(e) => setQuoteForm({ ...quoteForm, quote_delivery_days: e.target.value })}
                      placeholder="3"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Peça do seu catálogo (opcional)</label>
                  <select
                    value={quoteForm.quote_product_id}
                    onChange={(e) => setQuoteForm({ ...quoteForm, quote_product_id: e.target.value })}
                  >
                    <option value="">Nenhuma — só orçamento</option>
                    {myProducts.filter((p) => p.is_active).map((p) => (
                      <option key={p.id} value={p.id}>{p.name} — {formatCurrency(p.price)}</option>
                    ))}
                  </select>
                </div>
                <textarea
                  rows={2}
                  placeholder="Mensagem ou observações do orçamento..."
                  value={quoteForm.message || quoteForm.quote_notes}
                  onChange={(e) => setQuoteForm({ ...quoteForm, message: e.target.value, quote_notes: e.target.value })}
                />
                <div className="seller-product-actions">
                  <button type="button" className="btn btn-accent btn-sm" onClick={() => respond(req.id)}>
                    Enviar orçamento
                  </button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => setRespondingId(null)}>
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <div className="seller-product-actions">
                {req.already_responded ? (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      const conv = conversations.find((c) => c.request_id === req.id);
                      if (conv) openChat(conv.id);
                    }}
                  >
                    Ver conversa
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-accent btn-sm"
                    onClick={() => { setRespondingId(req.id); setQuoteForm(QUOTE_FORM_EMPTY); }}
                  >
                    Tenho essa peça
                  </button>
                )}
              </div>
            )}
          </article>
        ))}
      </div>

      <div className="part-request-chat">
        {activeConv ? (
          <>
            <div className="part-request-chat-head">
              <strong>{activeConv.buyer_name}</strong>
              <span>{activeConv.request_description}</span>
              {activeConv.quote_price && (
                <span>Orçamento: {formatCurrency(activeConv.quote_price)}</span>
              )}
              {activeConv.contact_phone && (
                <a className="btn-link" href={`tel:${activeConv.contact_phone}`}>
                  Ligar: {activeConv.contact_phone}
                </a>
              )}
              {activeConv.whatsapp_url && (
                <a className="btn btn-secondary btn-sm" href={activeConv.whatsapp_url} target="_blank" rel="noreferrer">
                  WhatsApp
                </a>
              )}
            </div>
            <div className="chat-messages">
              {messages.map((m) => (
                <div key={m.id} className={`chat-msg${m.is_mine ? ' mine' : ''}`}>
                  <span className="chat-msg-author">{m.is_mine ? 'Você' : m.sender_name}</span>
                  <p>{m.body}</p>
                </div>
              ))}
            </div>
            <form className="chat-input-row" onSubmit={send}>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Responder..." />
              <button type="submit" className="btn btn-accent btn-sm">Enviar</button>
            </form>
          </>
        ) : (
          <p className="state-empty">
            {conversations.length
              ? 'Selecione uma conversa ou responda a um pedido.'
              : 'Quando um cliente pedir uma peça que você tem, responda aqui.'}
          </p>
        )}
      </div>
    </div>
  );
}

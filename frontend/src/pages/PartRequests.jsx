import { useEffect, useState } from 'react';
import { Link, useOutletContext, useSearchParams } from 'react-router-dom';
import { api, getToken } from '../api/client';
import PageLoader from '../components/ui/PageLoader';
import { useToast } from '../context/ToastContext';

const EMPTY_FORM = {
  description: '',
  vehicle_brand: '',
  vehicle_model: '',
  vehicle_year: '',
  plate: '',
  vin: '',
  contact_phone: '',
  show_phone: true,
};

function formatVehicle(req) {
  const parts = [req.vehicle_brand, req.vehicle_model, req.vehicle_year].filter(Boolean);
  return parts.length ? parts.join(' · ') : null;
}

export default function PartRequests() {
  const { showToast } = useToast();
  const { openAuth, accountEmbedded } = useOutletContext() || {};
  const [searchParams] = useSearchParams();
  const [requests, setRequests] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [form, setForm] = useState({
    ...EMPTY_FORM,
    description: searchParams.get('q') ? `Preciso de ${searchParams.get('q')}` : '',
    vehicle_brand: searchParams.get('vehicle_brand') || '',
    vehicle_model: searchParams.get('vehicle_model') || '',
    vehicle_year: searchParams.get('vehicle_year') || '',
  });
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const [plateInput, setPlateInput] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [ratingForm, setRatingForm] = useState({ rating: 5, comment: '' });

  const load = async () => {
    if (!getToken()) { setLoading(false); return; }
    try {
      const [reqs, convs] = await Promise.all([
        api('/part-requests/'),
        api('/part-requests/conversations/'),
      ]);
      setRequests(reqs);
      setConversations(convs);
    } catch {
      setRequests([]);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const lookupPlate = async (e) => {
    e.preventDefault();
    if (!plateInput.trim()) return;
    setLookupLoading(true);
    try {
      const result = await api('/vehicles/lookup/', {
        method: 'POST',
        body: JSON.stringify({
          plate: plateInput.trim(),
          year: form.vehicle_year || undefined,
        }),
      });
      setForm({
        ...form,
        plate: plateInput.trim().toUpperCase(),
        vehicle_brand: result.brand_hint || form.vehicle_brand,
        vehicle_model: result.model_hint || form.vehicle_model,
        vehicle_year: result.year_hint || form.vehicle_year,
      });
      showToast(result.message || 'Veículo identificado!');
    } catch (err) {
      showToast(err.message || 'Não foi possível consultar a placa.');
    } finally {
      setLookupLoading(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!getToken()) {
      openAuth?.();
      return;
    }
    if (form.description.trim().length < 10) {
      showToast('Descreva a peça com pelo menos 10 caracteres');
      return;
    }
    try {
      await api('/part-requests/', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          vehicle_year: form.vehicle_year ? parseInt(form.vehicle_year, 10) : null,
        }),
      });
      showToast('Pedido publicado! Vendedores compatíveis serão notificados.');
      setForm(EMPTY_FORM);
      setPlateInput('');
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  const closeRequest = async (id, status) => {
    try {
      await api(`/part-requests/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      showToast(status === 'fulfilled' ? 'Pedido marcado como atendido' : 'Pedido encerrado');
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  const openChat = async (convId) => {
    setActiveConvId(convId);
    const msgs = await api(`/part-requests/chat/${convId}/messages/`);
    setMessages(msgs);
    load();
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

  const submitRating = async (convId) => {
    try {
      await api(`/part-requests/chat/${convId}/rate/`, {
        method: 'POST',
        body: JSON.stringify(ratingForm),
      });
      showToast('Avaliação enviada!');
      setRatingForm({ rating: 5, comment: '' });
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  const activeConv = conversations.find((c) => c.id === activeConvId);
  const openCount = requests.filter((r) => r.status === 'open').length;

  if (!getToken()) {
    if (accountEmbedded) return null;
    return (
      <div className="wrap part-requests-page">
        <span className="eyebrow">Pedido de peça</span>
        <h1>Não encontrou a peça?</h1>
        <p>Publique o que você precisa e receba contato de vendedores que têm em estoque.</p>
        <button type="button" className="btn btn-accent" onClick={() => openAuth?.()}>Entrar para solicitar</button>
      </div>
    );
  }

  const inner = (
    <>
      {!accountEmbedded && (
        <>
          <span className="eyebrow">Pedido de peça</span>
          <h1>Solicitações</h1>
        </>
      )}
      <p className={accountEmbedded ? 'form-hint' : 'page-lead'}>
        Descreva a peça que você precisa. Vendedores compatíveis são notificados.
        Pedidos expiram em 14 dias · máx. 3 abertos.
      </p>

      <form className="form-card part-request-form" onSubmit={submit}>
        <header className="form-card-head">
          <h2>Novo pedido</h2>
        </header>
        <div className="form-card-body">
        <div className="form-group">
          <label>O que você precisa? *</label>
          <textarea
            rows={3}
            placeholder="Ex: Alternador Gol G5 2012 1.6"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
          />
        </div>

        <div className="part-request-plate-lookup">
          <label>Identificar veículo pela placa</label>
          <div className="form-row">
            <input
              placeholder="ABC1D23"
              value={plateInput}
              onChange={(e) => setPlateInput(e.target.value.toUpperCase())}
            />
            <button type="button" className="btn btn-secondary btn-sm" disabled={lookupLoading} onClick={lookupPlate}>
              {lookupLoading ? 'Consultando...' : 'Consultar placa'}
            </button>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Marca do veículo</label>
            <input
              value={form.vehicle_brand}
              onChange={(e) => setForm({ ...form, vehicle_brand: e.target.value })}
              placeholder="Volkswagen"
            />
          </div>
          <div className="form-group">
            <label>Modelo</label>
            <input
              value={form.vehicle_model}
              onChange={(e) => setForm({ ...form, vehicle_model: e.target.value })}
              placeholder="Gol G5"
            />
          </div>
          <div className="form-group">
            <label>Ano</label>
            <input
              type="number"
              min="1980"
              max="2035"
              value={form.vehicle_year}
              onChange={(e) => setForm({ ...form, vehicle_year: e.target.value })}
              placeholder="2012"
            />
          </div>
        </div>
        <div className="form-group">
          <label>VIN (opcional)</label>
          <input
            value={form.vin}
            onChange={(e) => setForm({ ...form, vin: e.target.value.toUpperCase() })}
            placeholder="17 caracteres"
          />
        </div>
        <div className="form-group">
          <label>Telefone para contato</label>
          <input
            value={form.contact_phone}
            onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
            placeholder="(11) 99999-9999"
          />
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.show_phone}
            onChange={(e) => setForm({ ...form, show_phone: e.target.checked })}
          />
          <span>Exibir meu telefone para vendedores (além do chat)</span>
        </label>
        <p className="form-hint">{openCount}/3 pedidos abertos</p>
        <button type="submit" className="btn btn-accent" disabled={openCount >= 3}>Publicar pedido</button>
        </div>
      </form>

      {loading ? (
        <PageLoader />
      ) : (
        <>
          <h2 className="section-title">Meus pedidos ({requests.length})</h2>
          {!requests.length && (
            <p className="state-empty">Você ainda não fez nenhum pedido. <Link to="/pecas/">Buscar no catálogo</Link></p>
          )}
          {requests.map((req) => (
            <article key={req.id} className="part-request-card part-request-card--mine">
              <div className="part-request-card-head">
                <strong>{req.description}</strong>
                <span className={`status-pill status-${req.status}`}>{req.status_display}</span>
              </div>
              {formatVehicle(req) && <p className="part-request-vehicle">{formatVehicle(req)}</p>}
              <p className="seller-product-meta">
                {req.response_count} resposta(s) · {new Date(req.created_at).toLocaleDateString('pt-BR')}
                {req.days_until_expiry != null && req.status === 'open' && ` · expira em ${req.days_until_expiry}d`}
              </p>
              {req.status === 'open' && (
                <div className="seller-product-actions">
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => closeRequest(req.id, 'fulfilled')}>
                    Marcar atendido
                  </button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => closeRequest(req.id, 'closed')}>
                    Encerrar
                  </button>
                </div>
              )}
              {conversations.filter((c) => c.request_id === req.id).map((conv) => (
                <button
                  key={conv.id}
                  type="button"
                  className={`part-request-conv-btn${activeConvId === conv.id ? ' active' : ''}`}
                  onClick={() => openChat(conv.id)}
                >
                  <strong>{conv.seller_name}</strong>
                  {conv.quote_price && <span>Orçamento: R$ {Number(conv.quote_price).toFixed(2)}</span>}
                  {conv.last_message && <span>{conv.last_message}</span>}
                  {conv.rating && <span>{conv.rating.rating}★ avaliado</span>}
                  {conv.unread_count > 0 && <em>{conv.unread_count} nova(s)</em>}
                </button>
              ))}
            </article>
          ))}

          {activeConv && (
            <div className="part-request-chat part-request-chat--buyer">
              <h3>Chat com {activeConv.seller_name}</h3>
              <div className="chat-messages">
                {messages.map((m) => (
                  <div key={m.id} className={`chat-msg${m.is_mine ? ' mine' : ''}`}>
                    <span className="chat-msg-author">{m.is_mine ? 'Você' : m.sender_name}</span>
                    <p>{m.body}</p>
                  </div>
                ))}
              </div>
              {activeConv.request_status === 'open' ? (
                <form className="chat-input-row" onSubmit={send}>
                  <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Responder..." />
                  <button type="submit" className="btn btn-accent btn-sm">Enviar</button>
                </form>
              ) : (
                <>
                  <p className="form-hint">Este pedido foi encerrado.</p>
                  {!activeConv.rating && (
                    <div className="part-request-rating-form">
                      <p>Avalie o atendimento de {activeConv.seller_name}</p>
                      <select
                        value={ratingForm.rating}
                        onChange={(e) => setRatingForm({ ...ratingForm, rating: parseInt(e.target.value, 10) })}
                      >
                        {[5, 4, 3, 2, 1].map((n) => (
                          <option key={n} value={n}>{n} estrela(s)</option>
                        ))}
                      </select>
                      <input
                        placeholder="Comentário (opcional)"
                        value={ratingForm.comment}
                        onChange={(e) => setRatingForm({ ...ratingForm, comment: e.target.value })}
                      />
                      <button type="button" className="btn btn-accent btn-sm" onClick={() => submitRating(activeConv.id)}>
                        Enviar avaliação
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}
    </>
  );

  if (accountEmbedded) return <div className="part-requests-page">{inner}</div>;

  return <div className="wrap part-requests-page">{inner}</div>;
}

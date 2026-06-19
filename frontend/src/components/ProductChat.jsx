import { useEffect, useState } from 'react';
import { api, getToken } from '../api/client';
import { useToast } from '../context/ToastContext';

export default function ProductChat({ product }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [waUrl, setWaUrl] = useState('');

  useEffect(() => {
    if (product?.id) {
      api(`/products/${product.id}/whatsapp/`).then((d) => setWaUrl(d.url || '')).catch(() => {});
    }
  }, [product?.id]);

  const startChat = async () => {
    if (!getToken()) {
      showToast('Faça login para conversar com o vendedor');
      return;
    }
    if (!product.seller_id) {
      showToast('Peça vendida pela Galelugi — use o WhatsApp geral');
      return;
    }
    try {
      const conv = await api('/chat/start/', {
        method: 'POST',
        body: JSON.stringify({ product_id: product.id, message: 'Olá! Tenho interesse nesta peça.' }),
      });
      setConvId(conv.id);
      setOpen(true);
      loadMessages(conv.id);
    } catch (err) {
      showToast(err.message);
    }
  };

  const loadMessages = async (id) => {
    const msgs = await api(`/chat/${id}/messages/`);
    setMessages(msgs);
  };

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim() || !convId) return;
    try {
      await api(`/chat/${convId}/messages/`, {
        method: 'POST',
        body: JSON.stringify({ body: text.trim() }),
      });
      setText('');
      loadMessages(convId);
    } catch (err) {
      showToast(err.message);
    }
  };

  if (!product.seller_id && !waUrl) return null;

  return (
    <div className="product-chat">
      <div className="product-chat-actions">
        {product.seller_id && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={startChat}>
            Chat com vendedor
          </button>
        )}
        {waUrl && (
          <a href={waUrl} className="btn btn-whatsapp btn-sm" target="_blank" rel="noreferrer">
            WhatsApp {product.seller_name ? `— ${product.seller_name}` : ''}
          </a>
        )}
      </div>

      {open && convId && (
        <div className="chat-panel">
          <div className="chat-panel-head">
            <strong>Conversa sobre {product.name}</strong>
            <button type="button" onClick={() => setOpen(false)}>×</button>
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
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Digite sua mensagem..." />
            <button type="submit" className="btn btn-accent btn-sm">Enviar</button>
          </form>
        </div>
      )}
    </div>
  );
}

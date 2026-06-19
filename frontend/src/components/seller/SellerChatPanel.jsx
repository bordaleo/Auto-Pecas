import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import { useToast } from '../../context/ToastContext';

export default function SellerChatPanel() {
  const { showToast } = useToast();
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');

  const loadConversations = () => api('/chat/conversations/').then(setConversations).catch(() => {});

  useEffect(() => { loadConversations(); }, []);

  const openConv = async (id) => {
    setActiveId(id);
    const msgs = await api(`/chat/${id}/messages/`);
    setMessages(msgs);
    loadConversations();
  };

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim() || !activeId) return;
    try {
      await api(`/chat/${activeId}/messages/`, {
        method: 'POST',
        body: JSON.stringify({ body: text.trim() }),
      });
      setText('');
      openConv(activeId);
    } catch (err) {
      showToast(err.message);
    }
  };

  return (
    <div className="seller-chat-panel">
      <div className="seller-chat-list">
        <h3>Conversas ({conversations.length})</h3>
        {conversations.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`seller-chat-item${activeId === c.id ? ' active' : ''}`}
            onClick={() => openConv(c.id)}
          >
            <strong>{c.buyer_name}</strong>
            <span>{c.product_name}</span>
            {c.unread_count > 0 && <em>{c.unread_count} nova(s)</em>}
          </button>
        ))}
      </div>
      {activeId && (
        <div className="chat-panel">
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
        </div>
      )}
      {!activeId && conversations.length > 0 && (
        <p className="state-empty">Selecione uma conversa.</p>
      )}
      {!conversations.length && (
        <p className="state-empty">Nenhuma mensagem ainda. <Link to="/vender/">Publique peças</Link> para receber contatos.</p>
      )}
    </div>
  );
}

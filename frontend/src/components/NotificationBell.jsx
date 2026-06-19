import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, getToken } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function NotificationBell() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState([]);
  const ref = useRef(null);

  const load = () => {
    if (!getToken()) return;
    api('/notifications/unread/').then((d) => setUnread(d.unread_count || 0)).catch(() => {});
  };

  const loadList = () => {
    if (!getToken()) return;
    api('/notifications/').then((d) => {
      setItems(d.results || []);
      setUnread(d.unread_count || 0);
    }).catch(() => {});
  };

  useEffect(() => { load(); }, [user]);

  useEffect(() => {
    if (!getToken()) return undefined;
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, [user]);

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, []);

  if (!user) return null;

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) loadList();
  };

  const markAll = async () => {
    await api('/notifications/', { method: 'PATCH', body: JSON.stringify({ mark_all: true }) });
    loadList();
  };

  const markOne = async (notification) => {
    if (!notification.is_read) {
      await api('/notifications/', { method: 'PATCH', body: JSON.stringify({ ids: [notification.id] }) }).catch(() => {});
      setUnread((c) => Math.max(0, c - 1));
      setItems((prev) => prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n)));
    }
    setOpen(false);
  };

  return (
    <div className="notification-bell" ref={ref}>
      <button type="button" className="header-action notification-trigger" onClick={toggle} aria-label="Notificações">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unread > 0 && <em className="notification-badge">{unread > 9 ? '9+' : unread}</em>}
      </button>

      {open && (
        <div className="notification-panel">
          <div className="notification-panel-head">
            <strong>Notificações</strong>
            {unread > 0 && (
              <button type="button" className="btn-link" onClick={markAll}>Marcar todas lidas</button>
            )}
          </div>
          <div className="notification-list">
            {items.length === 0 ? (
              <p className="state-empty">Nenhuma notificação.</p>
            ) : (
              items.map((n) => (
                <Link
                  key={n.id}
                  to={n.link || '/'}
                  className={`notification-item${n.is_read ? '' : ' unread'}`}
                  onClick={() => markOne(n)}
                >
                  <strong>{n.title}</strong>
                  {n.body && <span>{n.body}</span>}
                  <time>{new Date(n.created_at).toLocaleString('pt-BR')}</time>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

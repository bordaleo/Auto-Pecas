import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

export default function PainelErrors() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); })
      .catch(() => navigate('/painel/entrar/'));
    painelApi('/painel/ops-events?limit=50')
      .then((data) => setEvents(data.results || []))
      .catch(() => {});
  }, [navigate]);

  return (
    <div>
      <h1>Alertas e erros</h1>
      <div className="painel-table">
        {events.length === 0 && <p>Nenhum evento registrado.</p>}
        {events.map((e) => (
          <div key={e.id} className="painel-error-card">
            <div className="painel-row">
              <strong>{e.category}</strong>
              <span>{new Date(e.created_at).toLocaleString('pt-BR')}</span>
            </div>
            <p>{e.message}</p>
            {e.detail && <pre className="painel-pre">{e.detail}</pre>}
          </div>
        ))}
      </div>
    </div>
  );
}

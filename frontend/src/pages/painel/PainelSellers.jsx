import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

export default function PainelSellers() {
  const navigate = useNavigate();
  const [sellers, setSellers] = useState([]);

  const load = () => {
    painelApi('/painel/sellers').then((data) => setSellers(data.results || [])).catch(() => {});
  };

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); else load(); })
      .catch(() => navigate('/painel/entrar/'));
  }, [navigate]);

  const setStatus = async (id, status) => {
    await painelApi('/painel/sellers', {
      method: 'PATCH',
      body: JSON.stringify({ id, status }),
    });
    load();
  };

  return (
    <div>
      <h1>Vendedores</h1>
      <div className="painel-table">
        {sellers.map((s) => (
          <div key={s.id} className="painel-row painel-seller-row">
            <div>
              <strong>{s.store_name}</strong>
              <div className="painel-row-meta">{s.user_email} · {s.status}</div>
            </div>
            {s.status === 'pending' && (
              <button type="button" className="btn btn-accent btn-sm" onClick={() => setStatus(s.id, 'active')}>Aprovar</button>
            )}
            {s.status === 'active' && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setStatus(s.id, 'suspended')}>Suspender</button>
            )}
            {s.status === 'suspended' && (
              <button type="button" className="btn btn-accent btn-sm" onClick={() => setStatus(s.id, 'active')}>Reativar</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

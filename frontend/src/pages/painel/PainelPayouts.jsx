import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatCurrency, painelApi } from '../../api/client';

export default function PainelPayouts() {
  const navigate = useNavigate();
  const [payouts, setPayouts] = useState([]);

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); })
      .catch(() => navigate('/painel/entrar/'));
    painelApi('/painel/payouts?status=pending').then((d) => setPayouts(d.results || [])).catch(() => {});
  }, [navigate]);

  const process = async (id, status) => {
    const payment_reference = status === 'paid' ? prompt('ID/comprovante PIX (opcional):') || '' : '';
    await painelApi('/painel/payouts', {
      method: 'PATCH',
      body: JSON.stringify({ id, status, payment_reference }),
    });
    const data = await painelApi('/painel/payouts?status=pending');
    setPayouts(data.results || []);
  };

  return (
    <div>
      <h1>Repasses a vendedores</h1>
      <p className="painel-sub">Processe saques via PIX manualmente.</p>
      {!payouts.length ? <p>Nenhum saque pendente.</p> : (
        <div className="painel-table">
          {payouts.map((p) => (
            <div key={p.id} className="painel-row" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
              <span>{p.store_name}</span>
              <span>{formatCurrency(p.amount)}</span>
              <span>{p.pix_key}</span>
              <span>{new Date(p.created_at).toLocaleDateString('pt-BR')}</span>
              <button type="button" className="btn btn-accent btn-sm" onClick={() => process(p.id, 'paid')}>Marcar pago</button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => process(p.id, 'rejected')}>Rejeitar</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

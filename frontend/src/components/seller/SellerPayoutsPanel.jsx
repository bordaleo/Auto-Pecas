import { useEffect, useState } from 'react';
import { api, formatCurrency } from '../../api/client';
import { useToast } from '../../context/ToastContext';

export default function SellerPayoutsPanel() {
  const { showToast } = useToast();
  const [data, setData] = useState(null);
  const [amount, setAmount] = useState('');
  const [pixKey, setPixKey] = useState('');

  const load = () => api('/seller/payouts/').then(setData).catch(() => {});

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (data?.pix_key) setPixKey(data.pix_key);
  }, [data?.pix_key]);

  if (!data) return <p className="state-empty">Carregando...</p>;

  const savePix = async () => {
    try {
      await api('/seller/payouts/', {
        method: 'PATCH',
        body: JSON.stringify({ pix_key: pixKey }),
      });
      showToast('Chave PIX salva');
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  const requestPayout = async (e) => {
    e.preventDefault();
    try {
      await api('/seller/payouts/request/', {
        method: 'POST',
        body: JSON.stringify({ amount: parseFloat(amount), pix_key: pixKey }),
      });
      showToast('Saque solicitado! Processamento em até 3 dias úteis.');
      setAmount('');
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  return (
    <div className="seller-payouts-panel">
      <div className="seller-stats">
        <article><strong>{formatCurrency(data.balance_available)}</strong><span>Saldo disponível</span></article>
        <article><strong>{formatCurrency(data.balance_pending)}</strong><span>Em processamento</span></article>
        <article><strong>{formatCurrency(data.minimum_payout)}</strong><span>Saque mínimo</span></article>
      </div>

      <div className="seller-form-card" style={{ marginTop: '1rem' }}>
        <h3>Chave PIX para repasse</h3>
        <div className="form-group">
          <input value={pixKey} onChange={(e) => setPixKey(e.target.value)} placeholder="CPF, e-mail, telefone ou chave aleatória" />
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={savePix}>Salvar PIX</button>
      </div>

      <form className="seller-form-card" style={{ marginTop: '1rem' }} onSubmit={requestPayout}>
        <h3>Solicitar saque</h3>
        <div className="form-group">
          <label>Valor (R$)</label>
          <input type="number" step="0.01" min={data.minimum_payout} value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </div>
        <button type="submit" className="btn btn-accent">Solicitar repasse via PIX</button>
      </form>

      <div className="seller-form-card" style={{ marginTop: '1rem' }}>
        <h3>Histórico de saques</h3>
        {(data.payouts || []).length === 0 ? (
          <p className="state-empty">Nenhum saque solicitado.</p>
        ) : (
          data.payouts.map((p) => (
            <div key={p.id} className="seller-product-row">
              <div>
                <strong>{formatCurrency(p.amount)}</strong>
                <div className="seller-product-meta">{p.status_display} · {new Date(p.created_at).toLocaleDateString('pt-BR')}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

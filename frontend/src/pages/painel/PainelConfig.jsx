import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

export default function PainelConfig() {
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); })
      .catch(() => navigate('/painel/entrar/'));
    painelApi('/admin/system-config').then(setConfig).catch(() => {});
  }, [navigate]);

  if (!config) return <p>Carregando...</p>;

  const update = (key, value) => setConfig((prev) => ({ ...prev, [key]: value }));

  const save = async (e) => {
    e.preventDefault();
    await painelApi('/admin/system-config', { method: 'PUT', body: JSON.stringify(config) });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div>
      <h1>Configurações da loja</h1>
      <form className="painel-form" onSubmit={save}>
        <label>Nome da loja<input value={config.store_name || ''} onChange={(e) => update('store_name', e.target.value)} /></label>
        <label>Slogan<input value={config.store_tagline || ''} onChange={(e) => update('store_tagline', e.target.value)} /></label>
        <label>WhatsApp<input value={config.store_whatsapp || ''} onChange={(e) => update('store_whatsapp', e.target.value)} /></label>
        <label>Frete grátis acima de (R$)<input type="number" step="0.01" value={config.free_shipping_min || ''} onChange={(e) => update('free_shipping_min', e.target.value)} /></label>
        <label>Comissão marketplace (%)<input type="number" step="0.01" value={config.marketplace_commission_percent || ''} onChange={(e) => update('marketplace_commission_percent', e.target.value)} /></label>
        <label>CEP origem (frete)<input value={config.origin_zip || ''} onChange={(e) => update('origin_zip', e.target.value)} placeholder="01310100" /></label>
        <label>Saque mínimo vendedor (R$)<input type="number" step="0.01" value={config.minimum_payout_amount || ''} onChange={(e) => update('minimum_payout_amount', e.target.value)} /></label>
        <label>Reserva estoque (min)<input type="number" value={config.stock_reservation_minutes || 30} onChange={(e) => update('stock_reservation_minutes', e.target.value)} /></label>
        <label>Token Melhor Envio<input value={config.melhor_envio_token || ''} onChange={(e) => update('melhor_envio_token', e.target.value)} placeholder="Opcional — usa tabela fixa se vazio" /></label>
        <label><input type="checkbox" checked={!!config.melhor_envio_sandbox} onChange={(e) => update('melhor_envio_sandbox', e.target.checked)} /> Melhor Envio sandbox</label>
        <label>Google Analytics ID<input value={config.google_analytics_id || ''} onChange={(e) => update('google_analytics_id', e.target.value)} placeholder="G-XXXXXXXX" /></label>
        <label>Meta Pixel ID<input value={config.meta_pixel_id || ''} onChange={(e) => update('meta_pixel_id', e.target.value)} placeholder="1234567890" /></label>
        <button type="submit" className="btn btn-accent">{saved ? 'Salvo!' : 'Salvar'}</button>
      </form>
    </div>
  );
}

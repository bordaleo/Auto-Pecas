import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, painelApi } from '../../api/client';
import { useToast } from '../../context/ToastContext';

export default function PainelConfig() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { showToast } = useToast();
  const [config, setConfig] = useState(null);
  const [meOAuth, setMeOAuth] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); })
      .catch(() => navigate('/painel/entrar/'));
    painelApi('/admin/system-config').then(setConfig).catch(() => {});
    api('/integrations/melhor-envio/info/').then(setMeOAuth).catch(() => setMeOAuth(null));
  }, [navigate]);

  useEffect(() => {
    const status = searchParams.get('melhor_envio');
    if (!status) return;
    if (status === 'connected') {
      showToast('Melhor Envio conectado! Token salvo.');
      painelApi('/admin/system-config').then(setConfig);
    } else if (status === 'error') {
      showToast(searchParams.get('detail') || 'Falha ao conectar Melhor Envio.');
    } else if (status === 'missing_code') {
      showToast('Autorização cancelada ou sem código.');
    }
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams, showToast]);

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

        <div className="painel-melhor-envio-box">
          <h3>Melhor Envio</h3>
          <p className="form-hint">
            App <strong>Galelugi Peças</strong> · Client ID configurado no servidor.
            {config.melhor_envio_token ? ' Token ativo.' : ' Conecte para obter o token automaticamente.'}
          </p>
          {meOAuth?.redirect_uri && (
            <p className="form-hint" style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>
              Callback: <code>{meOAuth.redirect_uri}</code>
            </p>
          )}
          <label><input type="checkbox" checked={!!config.melhor_envio_sandbox} onChange={(e) => update('melhor_envio_sandbox', e.target.checked)} /> Sandbox (homologação)</label>
          <label>Token (manual, opcional)<input value={config.melhor_envio_token || ''} onChange={(e) => update('melhor_envio_token', e.target.value)} placeholder="Preenchido automaticamente após conectar" /></label>
          {meOAuth?.authorize_url && (
            <a href={meOAuth.authorize_url} className="btn btn-secondary btn-sm" target="_blank" rel="noreferrer">
              Conectar Melhor Envio (autorizar)
            </a>
          )}
        </div>

        <label>Google Analytics ID<input value={config.google_analytics_id || ''} onChange={(e) => update('google_analytics_id', e.target.value)} placeholder="G-XXXXXXXX" /></label>
        <label>Meta Pixel ID<input value={config.meta_pixel_id || ''} onChange={(e) => update('meta_pixel_id', e.target.value)} placeholder="1234567890" /></label>
        <button type="submit" className="btn btn-accent">{saved ? 'Salvo!' : 'Salvar'}</button>
      </form>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

const STATUS_FILTERS = [
  { value: 'pending', label: 'Aguardando aprovação' },
  { value: '', label: 'Todas' },
  { value: 'active', label: 'Ativas' },
  { value: 'suspended', label: 'Suspensas' },
  { value: 'rejected', label: 'Rejeitadas' },
];

function DetailRow({ label, value }) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="painel-detail-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function PainelSellers() {
  const navigate = useNavigate();
  const [sellers, setSellers] = useState([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [selected, setSelected] = useState(null);
  const [rejectNotes, setRejectNotes] = useState('');

  const load = () => {
    const q = statusFilter ? `?status=${statusFilter}` : '';
    painelApi(`/painel/sellers${q}`)
      .then((data) => {
        setSellers(data.results || []);
        setPendingCount(data.pending_count || 0);
      })
      .catch(() => {});
  };

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); else load(); })
      .catch(() => navigate('/painel/entrar/'));
  }, [navigate, statusFilter]);

  const patchSeller = async (id, payload) => {
    await painelApi('/painel/sellers', {
      method: 'PATCH',
      body: JSON.stringify({ id, ...payload }),
    });
    setSelected(null);
    setRejectNotes('');
    load();
  };

  return (
    <div>
      <h1>Aprovação de vendedores</h1>
      <p className="painel-sub">
        Analise cada solicitação com calma. Aprovação costuma ser rápida — em geral no mesmo dia útil.
        {pendingCount > 0 && <strong> {pendingCount} aguardando.</strong>}
      </p>

      <div className="painel-toolbar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_FILTERS.map((opt) => (
            <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div className="painel-table">
        {sellers.length === 0 ? (
          <p className="state-empty">Nenhuma loja neste filtro.</p>
        ) : (
          sellers.map((s) => (
            <div key={s.id} className="painel-row painel-seller-row">
              <div>
                <strong>
                  {s.store_name}
                  {s.is_official && <span className="store-badge store-badge--sm">Oficial</span>}
                </strong>
                <div className="painel-row-meta">
                  {s.status_display || s.status} · {s.user_email}
                  {s.estimated_stock_units ? ` · ~${s.estimated_stock_units} peças` : ''}
                </div>
              </div>
              <div className="painel-seller-actions">
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setSelected(s)}>
                  Ver solicitação
                </button>
                {s.status === 'pending' && (
                  <button type="button" className="btn btn-accent btn-sm" onClick={() => patchSeller(s.id, { status: 'active' })}>
                    Aprovar
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {selected && (
        <div className="painel-modal-card painel-seller-detail">
          <h3>Solicitação — {selected.store_name}</h3>
          <p className="form-hint">Enviada em {new Date(selected.created_at).toLocaleString('pt-BR')}</p>

          <div className="painel-detail-grid">
            <DetailRow label="Responsável" value={selected.user_name} />
            <DetailRow label="E-mail da conta" value={selected.user_email} />
            <DetailRow label="Telefone (conta)" value={selected.user_phone} />
            <DetailRow label="Telefone / WhatsApp (loja)" value={selected.phone} />
            <DetailRow label="CPF ou CNPJ" value={selected.document} />
            <DetailRow label="Peças em estoque (aprox.)" value={selected.estimated_stock_units} />
            <DetailRow label="CEP de origem" value={selected.origin_zip} />
            <DetailRow label="Endereço" value={selected.shipping_address} />
            <DetailRow label="Cidade / UF" value={
              [selected.shipping_city, selected.shipping_state].filter(Boolean).join(' / ')
            }
            />
            <DetailRow label="Envio pela Sandroni" value={selected.ships_from_platform ? 'Sim' : 'Não'} />
            <DetailRow label="Chave PIX" value={selected.pix_key} />
          </div>

          {selected.description && (
            <div className="form-group">
              <label>Sobre a loja</label>
              <p className="painel-detail-text">{selected.description}</p>
            </div>
          )}

          {selected.status === 'pending' && (
            <>
              <div className="painel-modal-actions">
                <button type="button" className="btn btn-accent" onClick={() => patchSeller(selected.id, { status: 'active' })}>
                  Aprovar loja
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setSelected(null)}>Fechar</button>
              </div>
              <div className="form-group" style={{ marginTop: '1rem' }}>
                <label>Motivo da rejeição (opcional)</label>
                <textarea
                  rows={2}
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  placeholder="Ex.: documento incompleto"
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ marginTop: '0.5rem' }}
                  onClick={() => patchSeller(selected.id, { status: 'rejected', admin_notes: rejectNotes })}
                >
                  Rejeitar solicitação
                </button>
              </div>
            </>
          )}

          {selected.status !== 'pending' && (
            <div className="painel-modal-actions">
              {selected.status === 'active' && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => patchSeller(selected.id, { status: 'suspended' })}>
                  Suspender
                </button>
              )}
              {selected.status === 'suspended' && (
                <button type="button" className="btn btn-accent btn-sm" onClick={() => patchSeller(selected.id, { status: 'active' })}>
                  Reativar
                </button>
              )}
              {!selected.is_official && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => patchSeller(selected.id, { is_official: true })}>
                  Marcar oficial
                </button>
              )}
              <button type="button" className="btn btn-secondary" onClick={() => setSelected(null)}>Fechar</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

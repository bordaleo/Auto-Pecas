import { useEffect, useState } from 'react';
import { api, formatCurrency, getToken } from '../../api/client';
import { useToast } from '../../context/ToastContext';

export default function SellerAnalyticsPanel() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api('/seller/analytics/?days=30').then(setData).catch(() => {});
  }, []);

  if (!data) return <p className="state-empty">Carregando analytics...</p>;

  return (
    <div className="seller-analytics">
      <div className="seller-stats">
        <article><strong>{data.totals?.total_views || 0}</strong><span>Visualizações (30d)</span></article>
        <article><strong>{data.totals?.total_sales || 0}</strong><span>Vendas (30d)</span></article>
        <article><strong>{data.totals?.stale_products || 0}</strong><span>Peças paradas 30d+</span></article>
      </div>

      <h3>Performance por peça</h3>
      <div className="painel-table">
        {(data.products || []).map((p) => (
          <div key={p.id} className="painel-row">
            <span>{p.name}</span>
            <span>{p.views} views</span>
            <span>{p.sales} vendas</span>
            <span>{p.conversion_rate}% conv.</span>
            <span>{formatCurrency(p.revenue)}</span>
          </div>
        ))}
      </div>

      {(data.stale_products || []).length > 0 && (
        <>
          <h3>Peças paradas (sem venda há 30+ dias)</h3>
          <ul className="stale-list">
            {data.stale_products.map((p) => (
              <li key={p.id}>{p.name} — {p.views} views, estoque {p.stock}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function SellerCsvImportPanel() {
  const { showToast } = useToast();
  const [template, setTemplate] = useState('');

  useEffect(() => {
    api('/seller/products/import/template/').then((d) => {
      setTemplate(d.example || '');
    }).catch(() => {});
  }, []);

  const onUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/api/v1/seller/products/import/', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro na importação');
      showToast(`${data.created} peça(s) importada(s)!`);
      if (data.errors?.length) showToast(`${data.errors.length} linha(s) com erro.`);
    } catch (err) {
      showToast(err.message);
    }
    e.target.value = '';
  };

  return (
    <div className="seller-form-card">
      <h3>Importar peças via CSV</h3>
      <p className="seller-product-meta">
        Colunas obrigatórias: <strong>name, price, stock, image_url</strong>
      </p>
      <pre className="csv-template">{template}</pre>
      <input type="file" accept=".csv,text/csv" onChange={onUpload} />
    </div>
  );
}

export function SellerInvoicesPanel() {
  const { showToast } = useToast();
  const [rows, setRows] = useState([]);
  const [nuvemConfigured, setNuvemConfigured] = useState(false);
  const [nuvemMock, setNuvemMock] = useState(false);
  const [nuvemSandbox, setNuvemSandbox] = useState(true);
  const [emittingId, setEmittingId] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ status: 'processing', invoice_number: '', invoice_url: '', admin_notes: '' });

  const load = () => {
    api('/invoices/?scope=manage').then(setRows).catch(() => setRows([]));
  };

  useEffect(() => {
    load();
    api('/invoices/nuvem-fiscal/status')
      .then((data) => {
        setNuvemConfigured(Boolean(data.configured));
        setNuvemMock(Boolean(data.mock));
        setNuvemSandbox(Boolean(data.sandbox));
      })
      .catch(() => setNuvemConfigured(false));
  }, []);

  const filtered = statusFilter
    ? rows.filter((row) => row.status === statusFilter)
    : rows;

  const emitViaNuvem = async (rowId) => {
    setEmittingId(rowId);
    try {
      await api(`/invoices/${rowId}/emit/`, { method: 'POST' });
      showToast('NF-e enviada à Nuvem Fiscal. Aguarde a autorização.');
      load();
    } catch (err) {
      showToast(err.message);
    } finally {
      setEmittingId(null);
    }
  };

  const save = async () => {
    if (form.status === 'issued' && !form.invoice_number.trim()) {
      showToast('Informe o número da NF-e antes de marcar como emitida.');
      return;
    }
    if (form.status === 'issued' && !form.invoice_url.trim() && !rows.find((r) => r.id === editing)?.nuvem_fiscal_id) {
      showToast('Informe a URL do PDF ou emita via Nuvem Fiscal.');
      return;
    }
    try {
      await api(`/invoices/${editing}/`, { method: 'PATCH', body: JSON.stringify(form) });
      showToast('NF-e atualizada');
      setEditing(null);
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  return (
    <div className="seller-form-card">
      <h3>Solicitações de NF-e</h3>
      <p className="auth-step-hint">
        {nuvemConfigured
          ? (nuvemMock
            ? 'Modo simulação ativo — NF-e fictícia, sem chamada à Nuvem Fiscal.'
            : `Nuvem Fiscal ativa (${nuvemSandbox ? 'homologação' : 'produção'}). Você pode emitir automaticamente ou registrar manualmente.`)
          : 'Emita a nota no seu sistema fiscal e registre número + link do PDF aqui.'}
      </p>
      <div className="painel-toolbar" style={{ marginBottom: '1rem' }}>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Todas</option>
          <option value="requested">Solicitadas</option>
          <option value="processing">Em processamento</option>
          <option value="issued">Emitidas</option>
          <option value="rejected">Rejeitadas</option>
        </select>
      </div>
      {filtered.length === 0 ? (
        <p className="state-empty">Nenhuma solicitação neste filtro.</p>
      ) : (
        filtered.map((row) => (
          <div key={row.id} className="painel-row" style={{ flexWrap: 'wrap', gap: '0.5rem', alignItems: 'flex-start' }}>
            <div>
              <strong>Pedido #{row.order_id}</strong>
              <div>{row.company_name}</div>
              <small>{row.cnpj_formatted || row.cnpj} · {row.company_email || row.user_email}</small>
            </div>
            <span className={`invoice-status invoice-status--${row.status}`}>{row.status_display}</span>
            {row.nuvem_fiscal_status && (
              <small>API: {row.nuvem_fiscal_status}</small>
            )}
            {nuvemConfigured && row.status !== 'issued' && (
              <button
                type="button"
                className="btn btn-accent btn-sm"
                disabled={emittingId === row.id}
                onClick={() => emitViaNuvem(row.id)}
              >
                {emittingId === row.id ? 'Emitindo...' : (nuvemMock ? 'Simular NF-e' : 'Emitir via Nuvem Fiscal')}
              </button>
            )}
            {row.status === 'issued' && row.nuvem_fiscal_id && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={async () => {
                  try {
                    const response = await fetch(`/api/v1/invoices/${row.id}/nfe-pdf/`, {
                      headers: { Authorization: `Bearer ${getToken()}` },
                    });
                    if (!response.ok) throw new Error('Falha ao baixar PDF.');
                    const blob = await response.blob();
                    window.open(URL.createObjectURL(blob), '_blank', 'noopener,noreferrer');
                  } catch (err) {
                    showToast(err.message);
                  }
                }}
              >
                PDF
              </button>
            )}
            {row.status === 'issued' && row.invoice_url && !row.nuvem_fiscal_id && (
              <a href={row.invoice_url} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">PDF</a>
            )}
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => {
              setEditing(row.id);
              setForm({
                status: row.status === 'requested' ? 'processing' : row.status,
                invoice_number: row.invoice_number || '',
                invoice_url: row.invoice_url || '',
                admin_notes: row.admin_notes || '',
              });
            }}>
              Atualizar
            </button>
          </div>
        ))
      )}
      {editing && (
        <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--gl-border)' }}>
          <div className="form-group">
            <label>Status</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="processing">Em processamento</option>
              <option value="issued">Emitida</option>
              <option value="rejected">Rejeitada</option>
            </select>
          </div>
          <div className="form-group">
            <label>Número NF-e</label>
            <input value={form.invoice_number} onChange={(e) => setForm({ ...form, invoice_number: e.target.value })} />
          </div>
          <div className="form-group">
            <label>URL do PDF/XML</label>
            <input value={form.invoice_url} onChange={(e) => setForm({ ...form, invoice_url: e.target.value })} placeholder="https://..." />
          </div>
          <div className="form-group">
            <label>Observações (opcional)</label>
            <textarea rows={2} value={form.admin_notes} onChange={(e) => setForm({ ...form, admin_notes: e.target.value })} />
          </div>
          <button type="button" className="btn btn-accent btn-sm" onClick={save}>Salvar</button>
          <button type="button" className="btn btn-secondary btn-sm" style={{ marginLeft: '0.5rem' }} onClick={() => setEditing(null)}>Cancelar</button>
        </div>
      )}
    </div>
  );
}

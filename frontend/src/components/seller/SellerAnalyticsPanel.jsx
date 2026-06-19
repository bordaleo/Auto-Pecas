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
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ status: 'processing', invoice_number: '', invoice_url: '' });

  const load = () => {
    api('/invoices/?scope=manage').then(setRows).catch(() => setRows([]));
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
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
      {rows.length === 0 ? (
        <p className="state-empty">Nenhuma solicitação pendente.</p>
      ) : (
        rows.map((row) => (
          <div key={row.id} className="painel-row" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
            <span>Pedido #{row.order_id} · {row.company_name}</span>
            <span>{row.status_display}</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => {
              setEditing(row.id);
              setForm({
                status: row.status === 'requested' ? 'processing' : row.status,
                invoice_number: row.invoice_number || '',
                invoice_url: row.invoice_url || '',
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
            <label>URL do PDF</label>
            <input value={form.invoice_url} onChange={(e) => setForm({ ...form, invoice_url: e.target.value })} />
          </div>
          <button type="button" className="btn btn-accent btn-sm" onClick={save}>Salvar</button>
          <button type="button" className="btn btn-secondary btn-sm" style={{ marginLeft: '0.5rem' }} onClick={() => setEditing(null)}>Cancelar</button>
        </div>
      )}
    </div>
  );
}

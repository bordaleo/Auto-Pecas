import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

const STATUS_OPTIONS = [
  { value: '', label: 'Todas' },
  { value: 'requested', label: 'Solicitadas' },
  { value: 'processing', label: 'Em processamento' },
  { value: 'issued', label: 'Emitidas' },
  { value: 'rejected', label: 'Rejeitadas' },
];

export default function PainelInvoices() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [statusFilter, setStatusFilter] = useState('requested');
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    status: 'processing',
    invoice_number: '',
    invoice_url: '',
    admin_notes: '',
  });

  const load = async () => {
    const q = statusFilter ? `?status=${statusFilter}` : '';
    const data = await painelApi(`/painel/invoices${q}`);
    setRows(data.results || []);
  };

  useEffect(() => {
    painelApi('/painel/session')
      .then((d) => { if (!d.authenticated) navigate('/painel/entrar/'); })
      .catch(() => navigate('/painel/entrar/'));
    load().catch(() => setRows([]));
  }, [navigate, statusFilter]);

  const openEdit = (row) => {
    setEditing(row.id);
    setForm({
      status: row.status === 'requested' ? 'processing' : row.status,
      invoice_number: row.invoice_number || '',
      invoice_url: row.invoice_url || '',
      admin_notes: row.admin_notes || '',
    });
  };

  const save = async () => {
    await painelApi('/painel/invoices', {
      method: 'PATCH',
      body: JSON.stringify({ id: editing, ...form }),
    });
    setEditing(null);
    load();
  };

  return (
    <div>
      <h1>NF-e solicitadas</h1>
      <p className="painel-sub">Emita ou oriente vendedores sobre notas fiscais para pedidos B2B.</p>

      <div className="painel-toolbar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div className="painel-table">
        <div className="painel-table-row painel-table-head">
          <span>Pedido</span>
          <span>Empresa</span>
          <span>Loja</span>
          <span>Status</span>
          <span>Ações</span>
        </div>
        {rows.length === 0 ? (
          <p className="state-empty">Nenhuma solicitação neste filtro.</p>
        ) : (
          rows.map((row) => (
            <div key={row.id} className="painel-table-row">
              <span>#{row.order_id}</span>
              <span>
                <strong>{row.company_name}</strong>
                <small>{row.cnpj}</small>
              </span>
              <span>{row.seller_name}</span>
              <span>{row.status_display}</span>
              <span>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => openEdit(row)}>
                  Gerenciar
                </button>
              </span>
            </div>
          ))
        )}
      </div>

      {editing && (
        <div className="painel-modal-card">
          <h3>Solicitação #{editing}</h3>
          <div className="form-group">
            <label>Status</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="processing">Em processamento</option>
              <option value="issued">Emitida</option>
              <option value="rejected">Rejeitada</option>
            </select>
          </div>
          <div className="form-group">
            <label>Número da NF-e</label>
            <input value={form.invoice_number} onChange={(e) => setForm({ ...form, invoice_number: e.target.value })} />
          </div>
          <div className="form-group">
            <label>URL / PDF</label>
            <input value={form.invoice_url} onChange={(e) => setForm({ ...form, invoice_url: e.target.value })} placeholder="https://..." />
          </div>
          <div className="form-group">
            <label>Observações internas</label>
            <textarea rows={2} value={form.admin_notes} onChange={(e) => setForm({ ...form, admin_notes: e.target.value })} />
          </div>
          <div className="painel-modal-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setEditing(null)}>Cancelar</button>
            <button type="button" className="btn btn-accent" onClick={save}>Salvar</button>
          </div>
        </div>
      )}
    </div>
  );
}

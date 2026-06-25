import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken, productList } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import VehicleCompatibilityPicker from '../components/VehicleCompatibilityPicker';
import { PRODUCT_FIELD_LABELS, PRODUCT_FORM_FIELDS } from '../constants/productFields';

const EMPTY_FORM = {
  name: '',
  description: '',
  sku: '',
  oem_code: '',
  brand: '',
  price: '',
  cost_price: '',
  stock: '1',
  category: '',
  image_url: '',
  is_featured: false,
  is_active: true,
  part_condition: 'new',
  part_origin: 'original',
  warranty_days: '90',
};

export default function Manage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const { openAuth } = useOutletContext();
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [selectedVehicleCompat, setSelectedVehicleCompat] = useState([]);

  const loadProducts = () => {
    api('/manage/products/').then(setProducts).catch(() => setProducts([]));
  };

  useEffect(() => {
    if (!getToken() || !user?.is_staff) return;
    api('/categories/').then((data) => setCategories(productList(data)));
    loadProducts();
  }, [user]);

  if (!getToken()) {
    return (
      <div className="wrap">
        <p className="empty">
          <button type="button" className="btn btn-primary" onClick={() => openAuth('login')}>Entrar como admin</button>
        </p>
      </div>
    );
  }

  if (!user?.is_staff) {
    return <div className="wrap"><p className="empty">Acesso restrito a administradores.</p></div>;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (selectedVehicleCompat.length === 0) {
      showToast('Selecione ao menos um veículo compatível.');
      return;
    }
    const vehicle_compatibility = selectedVehicleCompat.map((e) => ({
      model_id: e.model_id,
      year_start: e.year_start,
      year_end: e.year_end,
    }));
    try {
      await api('/manage/products/', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          price: parseFloat(form.price),
          cost_price: form.cost_price ? parseFloat(form.cost_price) : null,
          stock: parseInt(form.stock, 10),
          category: form.category || null,
          warranty_days: parseInt(form.warranty_days, 10) || 0,
          vehicle_compatibility,
        }),
      });
      showToast('Peça cadastrada!');
      setForm(EMPTY_FORM);
      setSelectedVehicleCompat([]);
      loadProducts();
    } catch (error) {
      showToast(error.message);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append('file', file);
    try {
      const token = getToken();
      const res = await fetch('/api/v1/manage/upload-image/', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro no upload');
      setForm((prev) => ({ ...prev, image_url: data.url }));
      showToast('Imagem enviada!');
    } catch (error) {
      showToast(error.message);
    }
  };

  return (
    <div className="wrap" style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
      <form className="checkout-page" onSubmit={handleSubmit}>
        <h2 style={{ marginBottom: '1rem' }}>Nova peça</h2>
        {PRODUCT_FORM_FIELDS.map((field) => (
          <div className="form-group" key={field}>
            <label>{PRODUCT_FIELD_LABELS[field]}</label>
            <input
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              required={['name', 'price', 'stock'].includes(field)}
              type={field === 'price' || field === 'cost_price' || field === 'stock' ? 'number' : 'text'}
              step={field === 'price' || field === 'cost_price' ? '0.01' : undefined}
              min={field === 'stock' ? '0' : undefined}
            />
          </div>
        ))}
        <div className="form-group">
          <label>Descrição</label>
          <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <VehicleCompatibilityPicker
          selectedEntries={selectedVehicleCompat}
          onChange={setSelectedVehicleCompat}
          required
        />
        <div className="form-group">
          <label>Categoria</label>
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
            <option value="">Selecione uma categoria</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>
        <div className="form-row-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div className="form-group">
            <label>Condição</label>
            <select value={form.part_condition} onChange={(e) => setForm({ ...form, part_condition: e.target.value })}>
              <option value="new">Nova</option>
              <option value="used">Usada</option>
              <option value="reconditioned">Recondicionada</option>
            </select>
          </div>
          <div className="form-group">
            <label>Origem</label>
            <select value={form.part_origin} onChange={(e) => setForm({ ...form, part_origin: e.target.value })}>
              <option value="original">Original (OEM)</option>
              <option value="parallel">Paralela</option>
              <option value="remanufactured">Remanufaturada</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>Garantia (dias)</label>
          <input type="number" min="0" value={form.warranty_days} onChange={(e) => setForm({ ...form, warranty_days: e.target.value })} />
        </div>
        <div className="form-group">
          <label>Enviar foto</label>
          <input type="file" accept="image/*" onChange={handleUpload} />
        </div>
        <label><input type="checkbox" checked={form.is_featured} onChange={(e) => setForm({ ...form, is_featured: e.target.checked })} /> Destaque</label>
        <br />
        <label><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Ativo</label>
        <button type="submit" className="btn btn-primary btn-full" style={{ marginTop: '1rem' }}>Cadastrar</button>
      </form>

      <div className="checkout-page">
        <h2 style={{ marginBottom: '1rem' }}>Peças ({products.length})</h2>
        {products.map((product) => (
          <div key={product.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem 0', borderBottom: '1px solid rgba(0,0,0,.1)' }}>
            <div>
              <strong>{product.name}</strong>
              <div style={{ color: 'rgba(0,0,0,.55)', fontSize: '0.82rem' }}>
                {formatCurrency(product.price)}
                {product.cost_price && ` · Custo ${formatCurrency(product.cost_price)}`}
                {product.margin && ` · Margem ${product.margin.percent}%`}
                {' · Est: '}{product.stock}
              </div>
            </div>
            <Link to={`/peca/${product.slug}/`} className="btn btn-secondary btn-sm">Ver</Link>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken, productList } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export default function Manage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const { openAuth } = useOutletContext();
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState({
    name: '',
    description: '',
    sku: '',
    oem_code: '',
    brand: '',
    compatible_vehicles: '',
    price: '',
    stock: '1',
    category: '',
    image_url: '',
    is_featured: false,
    is_active: true,
  });

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
    try {
      await api('/manage/products/', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          price: parseFloat(form.price),
          stock: parseInt(form.stock, 10),
          category: form.category || null,
        }),
      });
      showToast('Peça cadastrada!');
      setForm({
        name: '', description: '', sku: '', oem_code: '', brand: '',
        compatible_vehicles: '', price: '', stock: '1', category: '',
        image_url: '', is_featured: false, is_active: true,
      });
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
        {['name', 'sku', 'oem_code', 'brand', 'price', 'stock', 'image_url'].map((field) => (
          <div className="form-group" key={field}>
            <label>{field}</label>
            <input
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              required={['name', 'price', 'stock'].includes(field)}
              type={field === 'price' || field === 'stock' ? 'number' : 'text'}
            />
          </div>
        ))}
        <div className="form-group">
          <label>Descrição</label>
          <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="form-group">
          <label>Veículos compatíveis</label>
          <textarea rows={2} value={form.compatible_vehicles} onChange={(e) => setForm({ ...form, compatible_vehicles: e.target.value })} />
        </div>
        <div className="form-group">
          <label>Categoria</label>
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
            <option value="">—</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Upload foto</label>
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
                {formatCurrency(product.price)} · Est: {product.stock}
              </div>
            </div>
            <Link to={`/peca/${product.slug}/`} className="btn btn-secondary btn-sm">Ver</Link>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken, productList } from '../api/client';
import { useStore } from '../context/StoreContext';
import { useToast } from '../context/ToastContext';

const EMPTY_FORM = {
  name: '', description: '', sku: '', oem_code: '', brand: '',
  compatible_vehicles: '', price: '', stock: '1', category: '',
  image_url: '', is_featured: false, is_active: true,
};

export default function SellerHub() {
  const { config } = useStore();
  const { showToast } = useToast();
  const { openAuth } = useOutletContext();
  const [seller, setSeller] = useState(null);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [applyForm, setApplyForm] = useState({ store_name: '', description: '', document: '', phone: '' });
  const [preview, setPreview] = useState(null);
  const [editingId, setEditingId] = useState(null);

  const commission = Number(config.marketplace_commission_percent || 12);

  const load = async () => {
    if (!getToken()) { setLoading(false); return; }
    try {
      const me = await api('/seller/me/');
      setSeller(me);
      const [cats, prods] = await Promise.all([
        api('/categories/'),
        api('/seller/products/'),
      ]);
      setCategories(productList(cats));
      setProducts(prods);
    } catch {
      setSeller(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const price = parseFloat(form.price);
    if (!seller || seller.status !== 'active' || !price || price <= 0) {
      setPreview(null);
      return;
    }
    const timer = setTimeout(() => {
      api('/seller/commission-preview/', {
        method: 'POST',
        body: JSON.stringify({ price }),
      }).then(setPreview).catch(() => setPreview(null));
    }, 400);
    return () => clearTimeout(timer);
  }, [form.price, seller]);

  if (!getToken()) {
    return (
      <div className="wrap seller-hub">
        <div className="seller-hero-card">
          <span className="eyebrow">Marketplace Galelugi</span>
          <h1>Venda suas peças para todo o Brasil</h1>
          <p>Cadastre sua loja, publique anúncios e receba após cada venda. A Galelugi cuida do checkout e pagamento.</p>
          <button type="button" className="btn btn-accent" onClick={() => openAuth('register')}>Criar conta e vender</button>
        </div>
      </div>
    );
  }

  if (loading) return <div className="wrap"><p className="state-empty">Carregando...</p></div>;

  if (!seller) {
    return (
      <div className="wrap seller-hub">
        <div className="seller-grid">
          <div className="seller-hero-card">
            <span className="eyebrow">Abra sua loja</span>
            <h1>Comece a vender na Galelugi</h1>
            <ul className="seller-benefits">
              <li>Publique peças em minutos</li>
              <li>Alcance compradores em todo o país</li>
              <li>Pagamento seguro via Mercado Pago</li>
              <li>Comissão transparente: <strong>{commission}%</strong> por venda</li>
            </ul>
          </div>
          <form className="seller-form-card" onSubmit={async (e) => {
            e.preventDefault();
            try {
              const data = await api('/seller/apply/', { method: 'POST', body: JSON.stringify(applyForm) });
              setSeller(data);
              showToast('Loja cadastrada!');
              load();
            } catch (err) { showToast(err.message); }
          }}>
            <h2>Cadastrar loja</h2>
            <div className="form-group">
              <label>Nome da loja *</label>
              <input value={applyForm.store_name} onChange={(e) => setApplyForm({ ...applyForm, store_name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>CPF ou CNPJ</label>
              <input value={applyForm.document} onChange={(e) => setApplyForm({ ...applyForm, document: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Telefone / WhatsApp</label>
              <input value={applyForm.phone} onChange={(e) => setApplyForm({ ...applyForm, phone: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Sobre sua loja</label>
              <textarea rows={3} value={applyForm.description} onChange={(e) => setApplyForm({ ...applyForm, description: e.target.value })} />
            </div>
            <button type="submit" className="btn btn-accent btn-full">Enviar cadastro</button>
          </form>
        </div>
      </div>
    );
  }

  if (seller.status === 'pending') {
    return (
      <div className="wrap seller-hub">
        <div className="seller-hero-card">
          <span className="eyebrow">Aguardando análise</span>
          <h1>Sua loja <em>{seller.store_name}</em> está em revisão</h1>
          <p>Em breve você poderá publicar peças. Enquanto isso, complete seu perfil em Minha conta.</p>
          <Link to="/perfil/" className="btn btn-secondary">Ir para minha conta</Link>
        </div>
      </div>
    );
  }

  if (seller.status === 'suspended') {
    return (
      <div className="wrap seller-hub">
        <p className="state-empty">Sua loja está suspensa. Entre em contato com o suporte.</p>
      </div>
    );
  }

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const data = await api('/seller/upload-image/', {
          method: 'POST',
          body: JSON.stringify({ image: reader.result }),
        });
        setForm((prev) => ({ ...prev, image_url: data.url }));
        showToast('Imagem enviada!');
      } catch (err) { showToast(err.message); }
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.image_url?.trim()) {
      showToast('Envie uma foto real da peça antes de publicar.');
      return;
    }
    try {
      if (editingId) {
        await api(`/seller/products/${editingId}/`, {
          method: 'PUT',
          body: JSON.stringify({
            ...form,
            price: parseFloat(form.price),
            stock: parseInt(form.stock, 10),
            category: form.category || null,
          }),
        });
        showToast('Peça atualizada!');
        setEditingId(null);
      } else {
        await api('/seller/products/', {
          method: 'POST',
          body: JSON.stringify({
            ...form,
            price: parseFloat(form.price),
            stock: parseInt(form.stock, 10),
            category: form.category || null,
          }),
        });
        showToast('Peça publicada!');
      }
      setForm(EMPTY_FORM);
      load();
    } catch (err) { showToast(err.message); }
  };

  const startEdit = (product) => {
    setEditingId(product.id);
    setForm({
      name: product.name || '',
      description: product.description || '',
      sku: product.sku || '',
      oem_code: product.oem_code || '',
      brand: product.brand || '',
      compatible_vehicles: product.compatible_vehicles || '',
      price: String(product.price || ''),
      stock: String(product.stock || '1'),
      category: product.category?.id || '',
      image_url: product.image_url || '',
      is_featured: product.is_featured || false,
      is_active: product.is_active !== false,
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const toggleActive = async (product) => {
    try {
      await api(`/seller/products/${product.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !product.is_active }),
      });
      showToast(product.is_active ? 'Peça inativada' : 'Peça reativada');
      load();
    } catch (err) { showToast(err.message); }
  };

  const stats = seller.stats || {};

  return (
    <div className="wrap seller-hub">
      <div className="seller-dash-head">
        <div>
          <span className="eyebrow">Minha loja</span>
          <h1>{seller.store_name}</h1>
          <p>Comissão Galelugi: <strong>{seller.commission_rate_default || commission}%</strong> por venda</p>
        </div>
        <Link to={`/loja/${seller.slug}/`} className="btn btn-secondary">Ver vitrine pública</Link>
      </div>

      <div className="seller-stats">
        <article><strong>{stats.products_active || 0}</strong><span>Peças ativas</span></article>
        <article><strong>{formatCurrency(stats.sales_earnings || 0)}</strong><span>Seu faturamento</span></article>
        <article><strong>{formatCurrency(stats.sales_gross || 0)}</strong><span>Vendas brutas</span></article>
      </div>

      <div className="seller-grid">
        <form className="seller-form-card" onSubmit={handleSubmit}>
          <h2>{editingId ? 'Editar peça' : 'Publicar nova peça'}</h2>
          <div className="form-group">
            <label>Nome *</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="form-row-2">
            <div className="form-group">
              <label>Preço de venda (R$) *</label>
              <input type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Estoque *</label>
              <input type="number" min="0" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} required />
            </div>
          </div>
          {preview && (
            <div className="commission-preview">
              <div><span>Comprador paga</span><strong>{formatCurrency(preview.price)}</strong></div>
              <div><span>Comissão Galelugi ({preview.commission_rate}%)</span><strong>- {formatCurrency(preview.platform_fee)}</strong></div>
              <div className="commission-preview-total"><span>Você recebe</span><strong>{formatCurrency(preview.seller_earning)}</strong></div>
            </div>
          )}
          <div className="form-group">
            <label>Marca</label>
            <input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
          </div>
          <div className="form-row-2">
            <div className="form-group">
              <label>SKU</label>
              <input value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Código OEM</label>
              <input value={form.oem_code} onChange={(e) => setForm({ ...form, oem_code: e.target.value })} />
            </div>
          </div>
          <div className="form-group">
            <label>Categoria</label>
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="">—</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Veículos compatíveis</label>
            <textarea rows={2} value={form.compatible_vehicles} onChange={(e) => setForm({ ...form, compatible_vehicles: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Descrição</label>
            <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="form-group">
            <label>URL da imagem *</label>
            <input value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Upload de foto *</label>
            <input type="file" accept="image/*" onChange={handleUpload} required={!form.image_url} />
          </div>
          {editingId && (
            <button type="button" className="btn btn-secondary btn-full" style={{ marginBottom: '0.5rem' }} onClick={() => { setEditingId(null); setForm(EMPTY_FORM); }}>
              Cancelar edição
            </button>
          )}
          <button type="submit" className="btn btn-accent btn-full">{editingId ? 'Salvar alterações' : 'Publicar peça'}</button>
        </form>

        <div className="seller-form-card">
          <h2>Minhas peças ({products.length})</h2>
          {products.length === 0 ? (
            <p className="state-empty" style={{ padding: '1.5rem 0' }}>Nenhuma peça publicada ainda.</p>
          ) : (
            <div className="seller-product-list">
              {products.map((p) => (
                <div key={p.id} className="seller-product-row">
                  <div>
                    <strong>{p.name}</strong>
                    <div className="seller-product-meta">
                      {formatCurrency(p.price)} · Estoque: {p.stock}
                      · Vendas: {p.sales_count || 0} ({formatCurrency(p.sales_revenue || 0)})
                      {!p.is_active && ' · Inativa'}
                    </div>
                  </div>
                  <div className="seller-product-actions">
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => startEdit(p)}>Editar</button>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => toggleActive(p)}>
                      {p.is_active ? 'Inativar' : 'Ativar'}
                    </button>
                    <Link to={`/peca/${p.slug}/`} className="btn btn-secondary btn-sm">Ver</Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

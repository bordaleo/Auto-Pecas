import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken, productList } from '../api/client';
import { useStore } from '../context/StoreContext';
import { useToast } from '../context/ToastContext';
import SellerOrdersPanel from '../components/seller/SellerOrdersPanel';
import SellerPayoutsPanel from '../components/seller/SellerPayoutsPanel';
import SellerReturnsPanel from '../components/seller/SellerReturnsPanel';
import SellerChatPanel from '../components/seller/SellerChatPanel';
import SellerPartRequestsPanel from '../components/seller/SellerPartRequestsPanel';
import SellerAnalyticsPanel, { SellerCsvImportPanel, SellerInvoicesPanel } from '../components/seller/SellerAnalyticsPanel';
import VehicleCompatibilityPicker from '../components/VehicleCompatibilityPicker';
import HubLayout from '../components/ui/HubLayout';
import PageLoader from '../components/ui/PageLoader';

const EMPTY_FORM = {
  name: '', description: '', sku: '', oem_code: '', brand: '',
  price: '', stock: '1', category: '',
  image_url: '', is_featured: false, is_active: true,
  part_condition: 'new', part_origin: 'original', warranty_days: '90',
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
  const [applyForm, setApplyForm] = useState({
    store_name: '', description: '', document: '', phone: '',
    origin_zip: '', shipping_address: '', shipping_city: '', shipping_state: '',
    estimated_stock_units: '',
  });
  const [shippingForm, setShippingForm] = useState({
    origin_zip: '', shipping_address: '', shipping_city: '', shipping_state: '',
    ships_from_platform: false,
  });
  const [preview, setPreview] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [section, setSection] = useState('products');
  const [subTab, setSubTab] = useState('orders');
  const [showImport, setShowImport] = useState(false);
  const [requestStats, setRequestStats] = useState({ unresponded_count: 0 });
  const [selectedVehicleModels, setSelectedVehicleModels] = useState([]);

  const commission = Number(config.marketplace_commission_percent || 8);

  const load = async () => {
    if (!getToken()) { setLoading(false); return; }
    try {
      const me = await api('/seller/me/');
      setSeller(me);
      setShippingForm({
        origin_zip: me.origin_zip || '',
        shipping_address: me.shipping_address || '',
        shipping_city: me.shipping_city || '',
        shipping_state: me.shipping_state || '',
        ships_from_platform: Boolean(me.ships_from_platform),
      });
      const [cats, prods] = await Promise.all([
        api('/categories/'),
        api('/seller/products/'),
      ]);
      setCategories(productList(cats));
      setProducts(prods);
      if (me.status === 'active') {
        api('/seller/part-requests/stats/').then(setRequestStats).catch(() => {});
      }
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

  if (loading) return <div className="wrap"><PageLoader /></div>;

  if (!seller) {
    return (
      <div className="wrap seller-hub">
        <div className="seller-grid">
          <div className="seller-hero-card">
            <span className="eyebrow">Abra sua loja</span>
            <h1>Comece a vender na Galelugi</h1>
            <p className="seller-fast-approval">
              Aprovação rápida — analisamos sua loja em até 1 dia útil e você recebe por e-mail quando estiver ativa.
            </p>
            <ul className="seller-benefits">
              <li>Publique peças em minutos</li>
              <li>Alcance compradores em todo o país</li>
              <li>Pagamento seguro via Mercado Pago</li>
              <li>Comissão transparente: <strong>{commission}%</strong> por venda</li>
            </ul>
          </div>
          <form className="form-card" onSubmit={async (e) => {
            e.preventDefault();
            const stock = parseInt(applyForm.estimated_stock_units, 10);
            if (!stock || stock < 1) {
              showToast('Informe quantas peças você tem em estoque (aproximado).');
              return;
            }
            try {
              const data = await api('/seller/apply/', {
                method: 'POST',
                body: JSON.stringify({
                  ...applyForm,
                  estimated_stock_units: stock,
                }),
              });
              setSeller(data);
              showToast('Solicitação enviada! Aprovação rápida — em breve você poderá vender.');
              load();
            } catch (err) { showToast(err.message); }
          }}>
            <header className="form-card-head">
              <h2>Cadastrar loja</h2>
              <p className="form-hint">Preencha com dados reais. Usamos essas informações para calcular frete e aprovar sua loja.</p>
            </header>
            <div className="form-card-body">
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
              <label>CEP de origem (frete)</label>
              <input value={applyForm.origin_zip} onChange={(e) => setApplyForm({ ...applyForm, origin_zip: e.target.value })} placeholder="00000-000" />
            </div>
            <div className="form-group">
              <label>Endereço de envio</label>
              <input value={applyForm.shipping_address} onChange={(e) => setApplyForm({ ...applyForm, shipping_address: e.target.value })} />
            </div>
            <div className="form-row form-row--2">
              <div className="form-group">
                <label>Cidade</label>
                <input value={applyForm.shipping_city} onChange={(e) => setApplyForm({ ...applyForm, shipping_city: e.target.value })} />
              </div>
              <div className="form-group">
                <label>UF</label>
                <input maxLength={2} value={applyForm.shipping_state} onChange={(e) => setApplyForm({ ...applyForm, shipping_state: e.target.value.toUpperCase() })} />
              </div>
            </div>
            <div className="form-group">
              <label>Quantidade de peças em estoque (aprox.) *</label>
              <input
                type="number"
                min="1"
                required
                value={applyForm.estimated_stock_units}
                onChange={(e) => setApplyForm({ ...applyForm, estimated_stock_units: e.target.value })}
                placeholder="Ex.: 150"
              />
              <small className="form-hint">Total de itens que você pretende vender na plataforma.</small>
            </div>
            <div className="form-group">
              <label>Sobre sua loja</label>
              <textarea rows={3} value={applyForm.description} onChange={(e) => setApplyForm({ ...applyForm, description: e.target.value })} />
            </div>
            <footer className="form-card-foot">
              <button type="submit" className="btn btn-accent">Enviar cadastro</button>
            </footer>
            </div>
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
          <p>
            Aprovação rápida — em geral no mesmo dia útil. Você receberá acesso completo assim que aprovada.
            {seller.estimated_stock_units ? ` Estoque informado: ~${seller.estimated_stock_units} peças.` : ''}
          </p>
          <Link to="/conta/" className="btn btn-secondary">Ir para minha conta</Link>
        </div>
      </div>
    );
  }

  if (seller.status === 'rejected') {
    return (
      <div className="wrap seller-hub">
        <div className="seller-hero-card">
          <span className="eyebrow">Solicitação não aprovada</span>
          <h1>Loja <em>{seller.store_name}</em></h1>
          <p>Entre em contato pelo WhatsApp se quiser mais detalhes ou enviar uma nova solicitação.</p>
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
    if (selectedVehicleModels.length === 0) {
      showToast('Selecione ao menos um veículo compatível.');
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
            warranty_days: parseInt(form.warranty_days, 10) || 90,
            category: form.category || null,
            vehicle_model_ids: selectedVehicleModels,
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
            warranty_days: parseInt(form.warranty_days, 10) || 90,
            category: form.category || null,
            vehicle_model_ids: selectedVehicleModels,
          }),
        });
        showToast('Peça publicada!');
      }
      setForm(EMPTY_FORM);
      setSelectedVehicleModels([]);
      load();
    } catch (err) { showToast(err.message); }
  };

  const startEdit = (product) => {
    setEditingId(product.id);
    const vehicleModels = product.vehicle_models || [];
    setSelectedVehicleModels(vehicleModels.map((v) => v.id));
    setForm({
      name: product.name || '',
      description: product.description || '',
      sku: product.sku || '',
      oem_code: product.oem_code || '',
      brand: product.brand || '',
      price: String(product.price || ''),
      stock: String(product.stock || '1'),
      category: product.category?.id || '',
      image_url: product.image_url || '',
      is_featured: product.is_featured || false,
      is_active: product.is_active !== false,
      part_condition: product.part_condition || 'new',
      part_origin: product.part_origin || 'original',
      warranty_days: String(product.warranty_days ?? '90'),
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

  const sellerNav = [
    { key: 'products', label: 'Peças e estoque' },
    { key: 'sales', label: 'Vendas' },
    { key: 'support', label: 'Atendimento', badge: requestStats.unresponded_count || 0 },
    { key: 'finance', label: 'Financeiro' },
    { key: 'settings', label: 'Configurações' },
  ];

  const handleSection = (key) => {
    setSection(key);
    if (key === 'sales') setSubTab('orders');
    if (key === 'support') setSubTab('requests');
    if (key === 'finance') setSubTab('payouts');
  };

  const salesTabs = [['orders', 'Pedidos'], ['returns', 'Devoluções']];
  const supportTabs = [['requests', 'Solicitações', requestStats.unresponded_count || 0], ['chat', 'Mensagens']];
  const financeTabs = [['payouts', 'Repasses'], ['analytics', 'Relatórios'], ['invoices', 'NF-e']];

  const subTabs = section === 'sales' ? salesTabs : section === 'support' ? supportTabs : section === 'finance' ? financeTabs : [];

  return (
    <div className="wrap seller-hub">
      <div className="seller-stats seller-stats--compact">
        <article><strong>{stats.products_active || 0}</strong><span>Peças ativas</span></article>
        <article><strong>{formatCurrency(stats.sales_earnings || 0)}</strong><span>Faturamento</span></article>
        <article><strong>{formatCurrency(seller.balance_available || 0)}</strong><span>Saldo</span></article>
      </div>

      <HubLayout
        eyebrow="Minha loja"
        title={(
          <>
            {seller.store_name}
            {seller.is_official && <span className="store-badge store-badge--lg">Oficial</span>}
          </>
        )}
        subtitle={`Comissão Galelugi: ${seller.commission_rate_default || commission}% por venda`}
        actions={<Link to={`/loja/${seller.slug}/`} className="btn btn-secondary btn-sm">Ver vitrine</Link>}
        nav={sellerNav}
        activeKey={section}
        onNavChange={handleSection}
        subTabs={subTabs}
        activeSubTab={subTab}
        onSubTabChange={setSubTab}
      >
        {section === 'sales' && subTab === 'orders' && <SellerOrdersPanel />}
        {section === 'sales' && subTab === 'returns' && <SellerReturnsPanel />}
        {section === 'support' && subTab === 'requests' && <SellerPartRequestsPanel />}
        {section === 'support' && subTab === 'chat' && <SellerChatPanel />}
        {section === 'finance' && subTab === 'payouts' && <SellerPayoutsPanel />}
        {section === 'finance' && subTab === 'analytics' && <SellerAnalyticsPanel />}
        {section === 'finance' && subTab === 'invoices' && <SellerInvoicesPanel />}

        {section === 'settings' && (
        <form
          className="form-card"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const data = await api('/seller/me/', {
                method: 'PATCH',
                body: JSON.stringify(shippingForm),
              });
              setSeller(data);
              showToast('Endereço de envio atualizado!');
            } catch (err) {
              showToast(err.message);
            }
          }}
        >
          <header className="form-card-head">
            <h2>Frete e endereço de origem</h2>
            <p className="form-hint">
              O frete do cliente é calculado a partir do CEP informado abaixo,
              ou do endereço da Sandroni se você usar envio pela plataforma.
            </p>
          </header>
          <div className="form-card-body">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={shippingForm.ships_from_platform}
              onChange={(e) => setShippingForm({ ...shippingForm, ships_from_platform: e.target.checked })}
            />
            <span>Envio pela Auto Peças Sandroni (consignação — peça sai do endereço da loja oficial)</span>
          </label>
          {!shippingForm.ships_from_platform && (
            <>
              <div className="form-group">
                <label>CEP de origem *</label>
                <input
                  value={shippingForm.origin_zip}
                  onChange={(e) => setShippingForm({ ...shippingForm, origin_zip: e.target.value })}
                  placeholder="00000-000"
                  required
                />
              </div>
              <div className="form-group">
                <label>Endereço</label>
                <input
                  value={shippingForm.shipping_address}
                  onChange={(e) => setShippingForm({ ...shippingForm, shipping_address: e.target.value })}
                />
              </div>
              <div className="form-row form-row--2">
                <div className="form-group">
                  <label>Cidade</label>
                  <input
                    value={shippingForm.shipping_city}
                    onChange={(e) => setShippingForm({ ...shippingForm, shipping_city: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>UF</label>
                  <input
                    maxLength={2}
                    value={shippingForm.shipping_state}
                    onChange={(e) => setShippingForm({ ...shippingForm, shipping_state: e.target.value.toUpperCase() })}
                  />
                </div>
              </div>
            </>
          )}
          <footer className="form-card-foot">
            <button type="submit" className="btn btn-accent">Salvar configurações de frete</button>
          </footer>
          </div>
        </form>
        )}

        {section === 'products' && (
      <div className="seller-grid">
        <div className="seller-products-toolbar">
          <p className="form-hint">Publique peças com foto real e compatibilidade veicular.</p>
          <button
            type="button"
            className={`btn btn-secondary btn-sm${showImport ? ' active' : ''}`}
            onClick={() => setShowImport((v) => !v)}
          >
            {showImport ? 'Fechar importação' : 'Importar CSV'}
          </button>
        </div>
        {showImport && (
          <div className="form-card" style={{ gridColumn: '1 / -1' }}>
            <SellerCsvImportPanel />
          </div>
        )}
        <form className="form-card" onSubmit={handleSubmit}>
          <header className="form-card-head">
            <h2>{editingId ? 'Editar peça' : 'Publicar nova peça'}</h2>
          </header>
          <div className="form-card-body">
          <div className="form-group">
            <label>Nome *</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="form-row form-row--2">
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
          <div className="form-row form-row--2">
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
            <label>Marca</label>
            <input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
          </div>
          <div className="form-row form-row--2">
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
          <VehicleCompatibilityPicker
            selectedIds={selectedVehicleModels}
            onChange={setSelectedVehicleModels}
            required
          />
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
          <footer className="form-card-foot">
          {editingId && (
            <button type="button" className="btn btn-secondary" onClick={() => { setEditingId(null); setForm(EMPTY_FORM); setSelectedVehicleModels([]); }}>
              Cancelar edição
            </button>
          )}
          <button type="submit" className="btn btn-accent">{editingId ? 'Salvar alterações' : 'Publicar peça'}</button>
          </footer>
          </div>
        </form>

        <div className="form-card">
          <header className="form-card-head">
            <h2>Minhas peças ({products.length})</h2>
          </header>
          <div className="form-card-body">
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
        )}
      </HubLayout>
    </div>
  );
}

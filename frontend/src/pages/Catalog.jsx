import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, productCount, productList } from '../api/client';
import ProductCard from '../components/ProductCard';

export default function Catalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [vehicleBrands, setVehicleBrands] = useState([]);
  const [vehicleModels, setVehicleModels] = useState([]);
  const [products, setProducts] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState('');
  const [vinInput, setVinInput] = useState('');
  const [vinYear, setVinYear] = useState('');
  const [lookupMode, setLookupMode] = useState('plate');
  const [vinResult, setVinResult] = useState(null);
  const [vinLoading, setVinLoading] = useState(false);

  const filters = useMemo(() => ({
    q: searchParams.get('q') || '',
    category: searchParams.get('category') || '',
    brand: searchParams.get('brand') || '',
    featured: searchParams.get('featured') || '',
    in_stock: searchParams.get('in_stock') || '',
    vehicle_brand: searchParams.get('vehicle_brand') || '',
    vehicle_model: searchParams.get('vehicle_model') || '',
    vehicle_year: searchParams.get('vehicle_year') || '',
  }), [searchParams]);

  const [draft, setDraft] = useState(filters);

  useEffect(() => {
    setDraft(filters);
  }, [filters]);

  useEffect(() => {
    Promise.all([api('/categories/'), api('/products/brands/'), api('/vehicles/brands/')])
      .then(([cats, brandList, vBrands]) => {
        setCategories(productList(cats));
        setBrands(brandList);
        setVehicleBrands(vBrands);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!draft.vehicle_brand) {
      setVehicleModels([]);
      return;
    }
    const q = new URLSearchParams({ brand: draft.vehicle_brand });
    if (draft.vehicle_year) q.set('year', draft.vehicle_year);
    api(`/vehicles/models/?${q}`).then(setVehicleModels).catch(() => setVehicleModels([]));
  }, [draft.vehicle_brand, draft.vehicle_year]);

  useEffect(() => {
    setLoading(true);
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    api(`/products/${query.toString() ? `?${query}` : ''}`)
      .then((data) => {
        let list = productList(data);
        if (sort === 'price_asc') list = [...list].sort((a, b) => a.price - b.price);
        if (sort === 'price_desc') list = [...list].sort((a, b) => b.price - a.price);
        setProducts(list);
        setCount(productCount(data, list));
      })
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [filters, sort]);

  const applyFilters = (event) => {
    event.preventDefault();
    const next = new URLSearchParams();
    if (draft.q) next.set('q', draft.q);
    if (draft.category) next.set('category', draft.category);
    if (draft.brand) next.set('brand', draft.brand);
    if (draft.featured) next.set('featured', draft.featured);
    if (draft.in_stock) next.set('in_stock', '1');
    if (draft.vehicle_brand) next.set('vehicle_brand', draft.vehicle_brand);
    if (draft.vehicle_model) next.set('vehicle_model', draft.vehicle_model);
    if (draft.vehicle_year) next.set('vehicle_year', draft.vehicle_year);
    setSearchParams(next);
  };

  const lookupVin = async (e) => {
    e.preventDefault();
    if (!vinInput.trim()) return;
    setVinLoading(true);
    setVinResult(null);
    try {
      const body = { year: vinYear || undefined };
      const trimmed = vinInput.trim();
      if (lookupMode === 'vin') {
        body.vin = trimmed;
      } else if (lookupMode === 'plate') {
        body.plate = trimmed.replace(/\s/g, '');
      } else {
        body.query = trimmed;
      }

      const data = await api('/vehicles/lookup/', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      setVinResult(data);
      if (data.year_hint && !vinYear) setVinYear(String(data.year_hint));

      const nextDraft = { ...draft };
      if (data.vehicle_models?.[0]) {
        const m = data.vehicle_models[0];
        nextDraft.vehicle_brand = m.brand_slug || '';
        nextDraft.vehicle_model = m.slug || '';
        nextDraft.vehicle_year = String(vinYear || data.year_hint || m.year_start || '');
      } else if (data.brand_hint || data.model_hint) {
        nextDraft.q = [data.brand_hint, data.model_hint].filter(Boolean).join(' ');
        if (vinYear || data.year_hint) nextDraft.vehicle_year = String(vinYear || data.year_hint);
      } else if (lookupMode === 'model') {
        nextDraft.q = trimmed;
      }
      setDraft(nextDraft);

      const next = new URLSearchParams();
      if (nextDraft.q) next.set('q', nextDraft.q);
      if (nextDraft.vehicle_brand) next.set('vehicle_brand', nextDraft.vehicle_brand);
      if (nextDraft.vehicle_model) next.set('vehicle_model', nextDraft.vehicle_model);
      if (nextDraft.vehicle_year) next.set('vehicle_year', nextDraft.vehicle_year);
      if ([...next.keys()].length) setSearchParams(next);

      if (data.products?.length) {
        setVinResult({
          ...data,
          message: `${data.message || 'Veículo identificado'} · ${data.products.length} peça(s) encontrada(s)`,
        });
      }
    } catch (err) {
      setVinResult({ error: true, message: err.message || 'Não foi possível consultar.' });
    } finally {
      setVinLoading(false);
    }
  };

  const retryWithYear = async () => {
    if (!vinInput.trim() || !vinYear) return;
    setVinLoading(true);
    try {
      const body = { year: vinYear };
      const trimmed = vinInput.trim();
      if (lookupMode === 'vin') body.vin = trimmed;
      else if (lookupMode === 'plate') body.plate = trimmed.replace(/\s/g, '');
      else body.query = trimmed;

      const data = await api('/vehicles/lookup/', { method: 'POST', body: JSON.stringify(body) });
      setVinResult({ ...data, year_estimated: false });
      if (data.vehicle_models?.[0]) {
        const m = data.vehicle_models[0];
        const next = new URLSearchParams();
        next.set('vehicle_brand', m.brand_slug || '');
        next.set('vehicle_model', m.slug || '');
        next.set('vehicle_year', vinYear);
        setSearchParams(next);
      }
    } catch (err) {
      setVinResult({ error: true, message: err.message || 'Não foi possível consultar.' });
    } finally {
      setVinLoading(false);
    }
  };

  return (
    <div className="wrap catalog-layout">
      <aside className="filters-panel">
        <div className="vin-lookup-box">
          <h3>Encontre peças do seu veículo</h3>
          <div className="vin-lookup-tabs">
            {[
              ['plate', 'Placa'],
              ['vin', 'VIN'],
              ['model', 'Modelo/Ano'],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`vin-lookup-tab${lookupMode === key ? ' active' : ''}`}
                onClick={() => { setLookupMode(key); setVinResult(null); }}
              >
                {label}
              </button>
            ))}
          </div>
          <form onSubmit={lookupVin}>
            <label className="vin-lookup-label">
              {lookupMode === 'plate' && 'Placa Mercosul ou antiga'}
              {lookupMode === 'vin' && 'VIN (17 caracteres)'}
              {lookupMode === 'model' && 'Modelo e motorização'}
            </label>
            <input
              className="vin-lookup-input"
              placeholder={
                lookupMode === 'plate' ? 'ABC1D23'
                  : lookupMode === 'vin' ? '9BWZZZ377VT004251'
                    : 'Polo 2010 1.6'
              }
              value={vinInput}
              onChange={(e) => setVinInput(lookupMode === 'plate' ? e.target.value.toUpperCase() : e.target.value)}
            />
            <label className="vin-lookup-label">Ano do veículo</label>
            <input
              className="vin-lookup-input"
              type="number"
              min="1980"
              max="2030"
              placeholder="Ex: 2010"
              value={vinYear}
              onChange={(e) => setVinYear(e.target.value)}
            />
            <button type="submit" className="btn btn-accent btn-full vin-lookup-submit" disabled={vinLoading}>
              {vinLoading ? 'Consultando...' : 'Buscar peças compatíveis'}
            </button>
          </form>
          {vinResult?.message && (
            <div className={`vin-lookup-result${vinResult.error ? ' error' : ''}`}>
              <p>{vinResult.message}</p>
              {vinResult.year_estimated && (
                <p className="vin-lookup-warning">
                  O ano retornado pela consulta pode estar incorreto. Confirme acima (ex.: 2010) e clique em atualizar.
                  <button type="button" className="btn-link" onClick={retryWithYear}>Atualizar com meu ano</button>
                </p>
              )}
            </div>
          )}
        </div>
        <h3>Filtrar</h3>
        <form onSubmit={applyFilters}>
          <div className="filter-row">
            <label htmlFor="filter-q">Busca</label>
            <input
              id="filter-q"
              value={draft.q}
              onChange={(e) => setDraft({ ...draft, q: e.target.value })}
            />
          </div>
          <div className="filter-row">
            <label htmlFor="filter-category">Categoria</label>
            <select
              id="filter-category"
              value={draft.category}
              onChange={(e) => setDraft({ ...draft, category: e.target.value })}
            >
              <option value="">Todas</option>
              {categories.map((cat) => (
                <option key={cat.slug} value={cat.slug}>{cat.name}</option>
              ))}
            </select>
          </div>
          <div className="filter-row">
            <label htmlFor="filter-brand">Marca</label>
            <select
              id="filter-brand"
              value={draft.brand}
              onChange={(e) => setDraft({ ...draft, brand: e.target.value })}
            >
              <option value="">Todas</option>
              {brands.map((brand) => (
                <option key={brand} value={brand}>{brand}</option>
              ))}
            </select>
          </div>
          <div className="filter-row">
            <label htmlFor="filter-vehicle-brand">Marca do veículo</label>
            <select
              id="filter-vehicle-brand"
              value={draft.vehicle_brand}
              onChange={(e) => setDraft({ ...draft, vehicle_brand: e.target.value, vehicle_model: '' })}
            >
              <option value="">Qualquer</option>
              {vehicleBrands.map((b) => (
                <option key={b.slug} value={b.slug}>{b.name}</option>
              ))}
            </select>
          </div>
          {vehicleModels.length > 0 && (
            <div className="filter-row">
              <label htmlFor="filter-vehicle-model">Modelo</label>
              <select
                id="filter-vehicle-model"
                value={draft.vehicle_model}
                onChange={(e) => setDraft({ ...draft, vehicle_model: e.target.value })}
              >
                <option value="">Qualquer</option>
                {vehicleModels.map((m) => (
                  <option key={m.slug} value={m.slug}>{m.name} ({m.year_start}-{m.year_end})</option>
                ))}
              </select>
            </div>
          )}
          <div className="filter-row">
            <label htmlFor="filter-vehicle-year">Ano</label>
            <input
              id="filter-vehicle-year"
              type="number"
              min="1980"
              max="2030"
              placeholder="Ex: 2015"
              value={draft.vehicle_year}
              onChange={(e) => setDraft({ ...draft, vehicle_year: e.target.value })}
            />
          </div>
          <div className="filter-row">
            <label>
              <input
                type="checkbox"
                checked={!!draft.in_stock}
                onChange={(e) => setDraft({ ...draft, in_stock: e.target.checked ? '1' : '' })}
              />
              {' '}Somente em estoque
            </label>
          </div>
          <button type="submit" className="btn btn-primary btn-full">Aplicar filtros</button>
        </form>
      </aside>

      <section>
        <div className="catalog-toolbar">
          <span>{loading ? 'Carregando...' : `${count} resultado(s)`}</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="">Mais relevantes</option>
            <option value="price_asc">Menor preço</option>
            <option value="price_desc">Maior preço</option>
          </select>
        </div>
        <div className="product-grid">
          {products.length ? (
            products.map((product) => <ProductCard key={product.id} product={product} />)
          ) : (
            <p className="empty">Nenhuma peça encontrada. <Link to="/pecas/">Ver todas</Link></p>
          )}
        </div>
      </section>
    </div>
  );
}

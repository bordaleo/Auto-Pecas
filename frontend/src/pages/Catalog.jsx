import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, fetchProductPages, productList } from '../api/client';
import ProductCard from '../components/ProductCard';

function buildQuery(filters, extra = {}) {
  const query = new URLSearchParams();
  Object.entries({ ...filters, ...extra }).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  return query;
}

export default function Catalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [vehicleBrands, setVehicleBrands] = useState([]);
  const [vehicleModels, setVehicleModels] = useState([]);
  const [modelSearch, setModelSearch] = useState('');
  const [products, setProducts] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [lookupProducts, setLookupProducts] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [vinInput, setVinInput] = useState('');
  const [vinYear, setVinYear] = useState('');
  const [lookupMode, setLookupMode] = useState('plate');
  const [vinResult, setVinResult] = useState(null);
  const [matchedModels, setMatchedModels] = useState([]);
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
    ordering: searchParams.get('ordering') || '',
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
    if (modelSearch.trim()) q.set('q', modelSearch.trim());
    api(`/vehicles/models/?${q}`).then(setVehicleModels).catch(() => setVehicleModels([]));
  }, [draft.vehicle_brand, draft.vehicle_year, modelSearch]);

  useEffect(() => {
    setLoading(true);
    const query = buildQuery(filters);
    const path = `/products/${query.toString() ? `?${query}` : ''}`;

    fetchProductPages(path, { maxPages: 3, pageSize: 60 })
      .then(({ results, count: total }) => {
        setProducts(results);
        setCount(total);
        setLookupProducts([]);

        if (!results.length) {
          const sq = buildQuery(filters);
          api(`/part-requests/suggestions/${sq.toString() ? `?${sq}` : ''}`)
            .then((d) => setSuggestions(d.products || []))
            .catch(() => setSuggestions([]));
        } else {
          setSuggestions([]);
        }
      })
      .catch(() => {
        setProducts([]);
        setCount(0);
      })
      .finally(() => setLoading(false));
  }, [filters]);

  const applyFilters = (event) => {
    event.preventDefault();
    const next = buildQuery({
      q: draft.q,
      category: draft.category,
      brand: draft.brand,
      featured: draft.featured,
      in_stock: draft.in_stock ? '1' : '',
      vehicle_brand: draft.vehicle_brand,
      vehicle_model: draft.vehicle_model,
      vehicle_year: draft.vehicle_year,
      ordering: filters.ordering,
    });
    setSearchParams(next);
  };

  const applyVehicleModel = (model) => {
    const nextDraft = {
      ...draft,
      vehicle_brand: model.brand_slug || draft.vehicle_brand,
      vehicle_model: model.slug,
      vehicle_year: draft.vehicle_year || String(model.year_start || ''),
      q: '',
    };
    setDraft(nextDraft);
    setSearchParams(buildQuery({
      vehicle_brand: nextDraft.vehicle_brand,
      vehicle_model: nextDraft.vehicle_model,
      vehicle_year: nextDraft.vehicle_year,
      ordering: filters.ordering,
    }));
  };

  const lookupVin = async (e) => {
    e.preventDefault();
    if (!vinInput.trim()) return;
    setVinLoading(true);
    setVinResult(null);
    setMatchedModels([]);
    setLookupProducts([]);
    try {
      const body = { year: vinYear || undefined };
      const trimmed = vinInput.trim();
      if (lookupMode === 'vin') body.vin = trimmed;
      else if (lookupMode === 'plate') body.plate = trimmed.replace(/\s/g, '');
      else body.query = trimmed;

      const data = await api('/vehicles/lookup/', {
        method: 'POST',
        body: JSON.stringify(body),
      });

      setVinResult(data);
      setMatchedModels(data.vehicle_models || []);
      if (data.year_hint && !vinYear) setVinYear(String(data.year_hint));

      const nextDraft = { ...draft, q: '' };
      if (data.vehicle_models?.length) {
        const m = data.vehicle_models[0];
        nextDraft.vehicle_brand = m.brand_slug || '';
        nextDraft.vehicle_model = m.slug || '';
        nextDraft.vehicle_year = String(vinYear || data.year_hint || m.year_start || '');
      } else if (data.brand_hint || data.model_hint) {
        nextDraft.q = [data.brand_hint, data.model_hint].filter(Boolean).join(' ');
        if (vinYear || data.year_hint) nextDraft.vehicle_year = String(vinYear || data.year_hint);
        const brand = vehicleBrands.find(
          (b) => b.name.toLowerCase() === (data.brand_hint || '').toLowerCase()
            || b.slug === (data.brand_slug || ''),
        );
        if (brand) nextDraft.vehicle_brand = brand.slug;
      } else if (lookupMode === 'model') {
        nextDraft.q = trimmed;
      }
      setDraft(nextDraft);

      const params = buildQuery({
        q: nextDraft.q,
        vehicle_brand: nextDraft.vehicle_brand,
        vehicle_model: nextDraft.vehicle_model,
        vehicle_year: nextDraft.vehicle_year,
        ordering: filters.ordering,
      });

      if (data.products?.length) {
        setLookupProducts(data.products);
      }

      if ([...params.keys()].length) setSearchParams(params);
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
      setMatchedModels(data.vehicle_models || []);
      if (data.vehicle_models?.[0]) {
        applyVehicleModel(data.vehicle_models[0]);
      }
    } catch (err) {
      setVinResult({ error: true, message: err.message || 'Não foi possível consultar.' });
    } finally {
      setVinLoading(false);
    }
  };

  const displayProducts = products.length ? products : lookupProducts;
  const showEmpty = !loading && !displayProducts.length;

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
                onClick={() => { setLookupMode(key); setVinResult(null); setMatchedModels([]); }}
              >
                {label}
              </button>
            ))}
          </div>
          <form onSubmit={lookupVin}>
            <label className="vin-lookup-label">
              {lookupMode === 'plate' && 'Placa Mercosul ou antiga'}
              {lookupMode === 'vin' && 'VIN (17 caracteres)'}
              {lookupMode === 'model' && 'Marca, modelo e motor (ex.: VW Polo 1.6)'}
            </label>
            <input
              className="vin-lookup-input"
              placeholder={
                lookupMode === 'plate' ? 'ABC1D23'
                  : lookupMode === 'vin' ? '9BWZZZ377VT004251'
                    : 'Volkswagen Polo 2014 1.6'
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
              placeholder="Ex: 2014"
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
                  Confirme o ano acima e clique em atualizar.
                  <button type="button" className="btn-link" onClick={retryWithYear}>Atualizar com meu ano</button>
                </p>
              )}
            </div>
          )}
          {matchedModels.length > 1 && (
            <div className="vehicle-model-chips">
              <p className="form-hint">Modelos identificados — selecione o correto:</p>
              {matchedModels.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className={`vehicle-model-chip${draft.vehicle_model === m.slug ? ' active' : ''}`}
                  onClick={() => applyVehicleModel(m)}
                >
                  {m.name}
                  {m.year_start ? ` (${m.year_start}–${m.year_end})` : ''}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="catalog-filters-box">
          <h3>Filtrar catálogo</h3>
          <form onSubmit={applyFilters}>
            <div className="filter-row">
              <label htmlFor="filter-q">Busca por palavras</label>
              <input
                id="filter-q"
                value={draft.q}
                onChange={(e) => setDraft({ ...draft, q: e.target.value })}
                placeholder="Ex.: pastilha freio dianteira"
              />
              <small className="form-hint">Cada palavra é buscada no nome, OEM, SKU e descrição.</small>
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
              <label htmlFor="filter-brand">Marca da peça</label>
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
            {draft.vehicle_brand && (
              <>
                <div className="filter-row">
                  <label htmlFor="filter-model-search">Buscar modelo</label>
                  <input
                    id="filter-model-search"
                    value={modelSearch}
                    onChange={(e) => setModelSearch(e.target.value)}
                    placeholder="Ex.: Gol, Onix, Civic..."
                  />
                </div>
                <div className="filter-row">
                  <label htmlFor="filter-vehicle-model">Modelo</label>
                  <select
                    id="filter-vehicle-model"
                    value={draft.vehicle_model}
                    onChange={(e) => setDraft({ ...draft, vehicle_model: e.target.value })}
                  >
                    <option value="">Qualquer modelo</option>
                    {vehicleModels.map((m) => (
                      <option key={`${m.slug}-${m.id}`} value={m.slug}>
                        {m.name} ({m.year_start}–{m.year_end})
                      </option>
                    ))}
                  </select>
                  {vehicleModels.length === 0 && (
                    <small className="form-hint">Nenhum modelo — aguarde a sincronização ou busque por palavras.</small>
                  )}
                </div>
              </>
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
        </div>
      </aside>

      <section>
        <div className="catalog-toolbar">
          <span className={`catalog-toolbar-status${loading ? ' is-loading' : ''}`}>
            {loading ? 'Carregando...' : `${count} resultado(s)`}
            {!loading && lookupProducts.length > 0 && !products.length && ' · sugestões por veículo'}
          </span>
          <select
            value={filters.ordering}
            onChange={(e) => {
              const next = buildQuery(filters, { ordering: e.target.value });
              if (!e.target.value) next.delete('ordering');
              setSearchParams(next);
            }}
          >
            <option value="">Mais relevantes</option>
            <option value="price_asc">Menor preço</option>
            <option value="price_desc">Maior preço</option>
            <option value="name">Nome A–Z</option>
          </select>
        </div>
        <div className="product-grid">
          {displayProducts.length ? (
            displayProducts.map((product) => <ProductCard key={product.id} product={product} />)
          ) : showEmpty ? (
            <div className="catalog-empty">
              <p className="empty">Nenhuma peça encontrada.</p>
              {suggestions.length > 0 && (
                <div className="catalog-suggestions">
                  <p>Talvez seja uma destas peças?</p>
                  <div className="product-grid product-grid--suggestions">
                    {suggestions.map((product) => (
                      <ProductCard key={product.id} product={product} />
                    ))}
                  </div>
                </div>
              )}
              <p>Não achou o que precisa? Publique um pedido e receba contato de vendedores.</p>
              <Link
                className="btn btn-accent"
                to={`/conta/solicitacoes/?${new URLSearchParams({
                  ...(filters.q ? { q: filters.q } : {}),
                  ...(filters.vehicle_brand ? { vehicle_brand: filters.vehicle_brand } : {}),
                  ...(filters.vehicle_model ? { vehicle_model: filters.vehicle_model } : {}),
                  ...(filters.vehicle_year ? { vehicle_year: filters.vehicle_year } : {}),
                }).toString()}`}
              >
                Criar pedido de peça
              </Link>
              <Link to="/pecas/" className="btn-link">Ver todas as peças</Link>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}

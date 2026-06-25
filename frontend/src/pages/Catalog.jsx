import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search, X, SlidersHorizontal } from 'lucide-react';
import { api, productList, productCount } from '../api/client';
import ProductCard from '../components/ProductCard';
import VehicleSelector from '../components/VehicleSelector';

const QUICK_SEARCHES = [
  'Pastilha de freio',
  'Filtro de ar',
  'Amortecedor',
  'Correia dentada',
  'Bateria',
  'Vela de ignição',
];

function buildQuery(filters, extra = {}) {
  const query = new URLSearchParams();
  Object.entries({ ...filters, ...extra }).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  return query;
}

function hasActiveFilters(filters) {
  return Boolean(
    filters.q || filters.category || filters.brand || filters.featured
    || filters.in_stock || filters.vehicle_brand || filters.vehicle_model || filters.vehicle_year,
  );
}

export default function Catalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [vehicleBrands, setVehicleBrands] = useState([]);
  const [products, setProducts] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [lookupProducts, setLookupProducts] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filtersLoading, setFiltersLoading] = useState(true);
  const [catalogError, setCatalogError] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [vinInput, setVinInput] = useState('');
  const [lookupMode, setLookupMode] = useState('plate');
  const [vinResult, setVinResult] = useState(null);
  const [lookupHintModels, setLookupHintModels] = useState([]);
  const [lookupModelHint, setLookupModelHint] = useState('');
  const [vehicleModelName, setVehicleModelName] = useState('');
  const [vinLoading, setVinLoading] = useState(false);
  const debounceRef = useRef(null);

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
  const [searchInput, setSearchInput] = useState(filters.q);

  useEffect(() => {
    setDraft(filters);
    setSearchInput(filters.q);
  }, [filters]);

  useEffect(() => {
    if (!filters.vehicle_model || !filters.vehicle_brand) {
      if (!filters.vehicle_model) setVehicleModelName('');
      return undefined;
    }

    let cancelled = false;
    const params = new URLSearchParams({
      brand: filters.vehicle_brand,
      limit: '500',
    });
    api(`/vehicles/models/?${params}`)
      .then((data) => {
        if (cancelled) return;
        const match = productList(data).find((m) => m.slug === filters.vehicle_model);
        if (match?.name) setVehicleModelName(match.name);
      })
      .catch(() => {});

    return () => { cancelled = true; };
  }, [filters.vehicle_brand, filters.vehicle_model]);

  useEffect(() => {
    setFiltersLoading(true);
    setCatalogError('');
    api('/catalog/filters/')
      .then((data) => {
        setCategories(productList(data.categories));
        setBrands(data.product_brands || []);
        setVehicleBrands(data.vehicle_brands || []);
      })
      .catch(() => api('/categories/').then((cats) => {
        setCategories(productList(cats));
        return Promise.all([api('/products/brands/'), api('/vehicles/brands/')]);
      }).then(([brandList, vBrands]) => {
        setBrands(brandList);
        setVehicleBrands(vBrands);
      }))
      .catch(() => setCatalogError('Não foi possível carregar os filtros. Verifique se o servidor está online.'))
      .finally(() => setFiltersLoading(false));
  }, []);

  useEffect(() => {
    setLoading(true);
    setCatalogError('');
    const query = buildQuery(filters);
    const path = `/products/${query.toString() ? `?${query}` : ''}`;

    api(path)
      .then((data) => {
        const results = productList(data);
        setProducts(results);
        setCount(productCount(data, results));
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
        setCatalogError('Erro ao carregar peças. Confirme que o backend está rodando.');
      })
      .finally(() => setLoading(false));
  }, [filters]);

  const pushFilters = (nextDraft) => {
    setSearchParams(buildQuery({
      q: nextDraft.q,
      category: nextDraft.category,
      brand: nextDraft.brand,
      featured: nextDraft.featured,
      in_stock: nextDraft.in_stock ? '1' : '',
      vehicle_brand: nextDraft.vehicle_brand,
      vehicle_model: nextDraft.vehicle_model,
      vehicle_year: nextDraft.vehicle_year,
      ordering: filters.ordering,
    }));
  };

  const scheduleSearch = (value) => {
    setSearchInput(value);
    setDraft((prev) => ({ ...prev, q: value }));
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value.trim()) next.set('q', value.trim());
        else next.delete('q');
        return next;
      });
    }, 450);
  };

  const submitSearch = (event) => {
    event.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const value = searchInput.trim();
    setDraft((prev) => ({ ...prev, q: value }));
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set('q', value);
      else next.delete('q');
      return next;
    });
  };

  const applyFilters = (event) => {
    event.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setSearchInput(draft.q);
    pushFilters(draft);
    setFiltersOpen(false);
  };

  const clearFilters = () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setSearchInput('');
    setVehicleModelName('');
    setSearchParams(new URLSearchParams(filters.ordering ? { ordering: filters.ordering } : {}));
  };

  const removeFilter = (key) => {
    const next = { ...draft, [key]: '' };
    if (key === 'vehicle_brand') {
      next.vehicle_model = '';
      next.vehicle_year = '';
      setVehicleModelName('');
    }
    if (key === 'vehicle_model') {
      next.vehicle_year = '';
      setVehicleModelName('');
    }
    if (key === 'q') setSearchInput('');
    setDraft(next);
    pushFilters(next);
  };

  const handleVehicleChange = (patch) => {
    if (patch.vehicle_model_name !== undefined) {
      setVehicleModelName(patch.vehicle_model_name || '');
    }
    if (patch.vehicle_model === '') setVehicleModelName('');
    if (patch.vehicle_brand === '') setVehicleModelName('');
    setDraft((prev) => {
      const { vehicle_model_name, ...rest } = patch;
      return { ...prev, ...rest };
    });
  };

  const applyVehicleSelection = (nextDraft) => {
    if (nextDraft.vehicle_brand && nextDraft.vehicle_model) {
      pushFilters(nextDraft);
    }
  };

  const lookupVin = async (e) => {
    e.preventDefault();
    if (!vinInput.trim()) return;
    setVinLoading(true);
    setVinResult(null);
    setLookupHintModels([]);
    setLookupModelHint('');
    setLookupProducts([]);
    try {
      const body = { year: draft.vehicle_year || undefined };
      const trimmed = vinInput.trim();
      if (lookupMode === 'vin') body.vin = trimmed;
      else if (lookupMode === 'plate') body.plate = trimmed.replace(/\s/g, '');
      else body.query = trimmed;

      const data = await api('/vehicles/lookup/', {
        method: 'POST',
        body: JSON.stringify(body),
      });

      setVinResult(data);
      setLookupHintModels(data.vehicle_models || []);
      setLookupModelHint(data.model_hint || '');

      const nextDraft = { ...draft, q: '', vehicle_model: '' };
      const brandSlug = data.vehicle_models?.[0]?.brand_slug
        || vehicleBrands.find(
          (b) => b.name.toLowerCase() === (data.brand_hint || '').toLowerCase(),
        )?.slug
        || '';
      if (brandSlug) nextDraft.vehicle_brand = brandSlug;
      if (data.year_hint) nextDraft.vehicle_year = String(data.year_hint);

      if (!data.vehicle_models?.length && (data.brand_hint || data.model_hint)) {
        nextDraft.q = [data.brand_hint, data.model_hint].filter(Boolean).join(' ');
      } else if (lookupMode === 'model' && !brandSlug) {
        nextDraft.q = trimmed;
      }

      setDraft(nextDraft);
      setSearchInput(nextDraft.q || '');
      if (data.products?.length) setLookupProducts(data.products);
      if (nextDraft.q) pushFilters(nextDraft);
    } catch (err) {
      setVinResult({ error: true, message: err.message || 'Não foi possível consultar.' });
    } finally {
      setVinLoading(false);
    }
  };

  const retryWithYear = async () => {
    if (!vinInput.trim() || !draft.vehicle_year) return;
    lookupVin({ preventDefault: () => {} });
  };

  const filterChips = useMemo(() => {
    const vehicle = [];
    const parts = [];
    const other = [];

    if (filters.vehicle_brand) {
      const vb = vehicleBrands.find((b) => b.slug === filters.vehicle_brand);
      vehicle.push({ key: 'vehicle_brand', label: vb?.name || filters.vehicle_brand, group: 'vehicle' });
    }
    if (filters.vehicle_model) {
      vehicle.push({
        key: 'vehicle_model',
        label: vehicleModelName || filters.vehicle_model.replace(/-/g, ' '),
        group: 'vehicle',
      });
    }
    if (filters.vehicle_year) {
      vehicle.push({ key: 'vehicle_year', label: `Ano ${filters.vehicle_year}`, group: 'vehicle' });
    }
    if (filters.q) parts.push({ key: 'q', label: filters.q, group: 'parts' });
    if (filters.category) {
      const cat = categories.find((c) => c.slug === filters.category);
      parts.push({ key: 'category', label: cat?.name || filters.category, group: 'parts' });
    }
    if (filters.brand) parts.push({ key: 'brand', label: filters.brand, group: 'parts' });
    if (filters.in_stock) other.push({ key: 'in_stock', label: 'Em estoque', group: 'other' });
    if (filters.featured) other.push({ key: 'featured', label: 'Destaques', group: 'other' });

    return { vehicle, parts, other, all: [...vehicle, ...parts, ...other] };
  }, [filters, categories, vehicleBrands, vehicleModelName]);

  const displayProducts = products.length ? products : lookupProducts;
  const showEmpty = !loading && !displayProducts.length;

  return (
    <div className="catalog-page">
      <header className="catalog-hero wrap">
        <div className="catalog-hero__head">
          <div>
            <h1 className="catalog-hero__title">Catálogo de peças</h1>
            <p className="catalog-hero__subtitle">
              Busque por nome, OEM, SKU, marca ou veículo compatível
            </p>
          </div>
          <button
            type="button"
            className="catalog-filters-toggle"
            onClick={() => setFiltersOpen((v) => !v)}
            aria-expanded={filtersOpen}
          >
            <SlidersHorizontal size={16} aria-hidden="true" />
            Filtros
          </button>
        </div>

        <form className="catalog-search" onSubmit={submitSearch}>
          <Search className="catalog-search__icon" size={20} aria-hidden="true" />
          <input
            type="search"
            className="catalog-search__input"
            placeholder="Ex.: pastilha freio Gol 2014, filtro ar, OEM 12345..."
            value={searchInput}
            onChange={(e) => scheduleSearch(e.target.value)}
            aria-label="Buscar peças"
          />
          {searchInput && (
            <button
              type="button"
              className="catalog-search__clear"
              onClick={() => scheduleSearch('')}
              aria-label="Limpar busca"
            >
              <X size={16} />
            </button>
          )}
          <button type="submit" className="btn btn-accent catalog-search__btn">
            Buscar
          </button>
        </form>

        <div className="catalog-quick-tags">
          {QUICK_SEARCHES.map((tag) => (
            <button
              key={tag}
              type="button"
              className="catalog-quick-tag"
              onClick={() => scheduleSearch(tag)}
            >
              {tag}
            </button>
          ))}
        </div>

        {filterChips.all.length > 0 && (
          <div className="catalog-active-filters">
            {filterChips.vehicle.length > 0 && (
              <div className="catalog-active-filters__group">
                <span className="catalog-active-filters__label">Veículo</span>
                <div className="catalog-active-filters__chips">
                  {filterChips.vehicle.map((chip) => (
                    <button
                      key={chip.key}
                      type="button"
                      className="catalog-active-filters__chip catalog-active-filters__chip--vehicle"
                      onClick={() => removeFilter(chip.key)}
                    >
                      {chip.label}
                      <X size={12} aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </div>
            )}
            {(filterChips.parts.length > 0 || filterChips.other.length > 0) && (
              <div className="catalog-active-filters__group">
                <span className="catalog-active-filters__label">Filtros</span>
                <div className="catalog-active-filters__chips">
                  {[...filterChips.parts, ...filterChips.other].map((chip) => (
                    <button
                      key={chip.key}
                      type="button"
                      className="catalog-active-filters__chip"
                      onClick={() => removeFilter(chip.key)}
                    >
                      {chip.label}
                      <X size={12} aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </div>
            )}
            <button type="button" className="catalog-active-filters__clear" onClick={clearFilters}>
              Limpar tudo
            </button>
          </div>
        )}

        {catalogError && (
          <div className="catalog-alert catalog-alert--error" role="alert">
            {catalogError}
          </div>
        )}
      </header>

      <div className="wrap catalog-layout">
        <aside className={`filters-panel${filtersOpen ? ' is-open' : ''}`}>
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
                  onClick={() => { setLookupMode(key); setVinResult(null); setLookupHintModels([]); setLookupModelHint(''); }}
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
            <button type="submit" className="btn btn-accent btn-full vin-lookup-submit" disabled={vinLoading}>
              {vinLoading ? 'Consultando...' : 'Identificar veículo'}
            </button>
          </form>
          {vinResult?.message && !vinResult.error && (
            <div className="vin-lookup-result vin-lookup-result--success">
              <p className="vin-lookup-result__vehicle">{vinResult.message}</p>
              {vinResult.year_estimated && (
                <p className="vin-lookup-warning">
                  Confirme o ano no passo 4 abaixo.
                  <button type="button" className="btn-link" onClick={retryWithYear}>Atualizar busca</button>
                </p>
              )}
            </div>
          )}
          {vinResult?.error && (
            <div className="vin-lookup-result error">
              <p>{vinResult.message}</p>
            </div>
          )}

          <VehicleSelector
            brands={vehicleBrands}
            brand={draft.vehicle_brand}
            modelSlug={draft.vehicle_model}
            year={draft.vehicle_year}
            onChange={(patch) => {
              handleVehicleChange(patch);
              const { vehicle_model_name, ...filterPatch } = patch;
              const merged = { ...draft, ...filterPatch };
              const modelSelected = 'vehicle_model' in patch && patch.vehicle_model;
              const yearChanged = 'vehicle_year' in patch;
              if (merged.vehicle_brand && merged.vehicle_model && (modelSelected || yearChanged)) {
                applyVehicleSelection(merged);
              }
            }}
            disabled={filtersLoading || vinLoading}
            hintModels={lookupHintModels}
            modelHint={lookupModelHint || vinResult?.model_hint || ''}
            yearHint={vinResult?.year_hint || ''}
          />
        </div>

          <div className="catalog-filters-box">
            <h3>Filtrar catálogo</h3>
            <form onSubmit={applyFilters}>
              <div className="filter-row">
                <label htmlFor="filter-category">Categoria</label>
                <select
                  id="filter-category"
                  value={draft.category}
                  onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                  disabled={filtersLoading}
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
                  disabled={filtersLoading}
                >
                  <option value="">Todas</option>
                  {brands.map((brand) => (
                    <option key={brand} value={brand}>{brand}</option>
                  ))}
                </select>
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
              {hasActiveFilters(filters) && (
                <button type="button" className="btn btn-secondary btn-full catalog-clear-btn" onClick={clearFilters}>
                  Limpar filtros
                </button>
              )}
            </form>
          </div>
        </aside>

        <section className="catalog-results">
          <div className="catalog-toolbar">
            <span className={`catalog-toolbar-status${loading ? ' is-loading' : ''}`}>
              {loading ? 'Carregando peças...' : `${count} resultado(s)`}
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

          <div className="product-grid product-grid--catalog">
            {displayProducts.length ? (
              displayProducts.map((product) => (
                <ProductCard key={product.id} product={product} variant="catalog" />
              ))
            ) : showEmpty ? (
              <div className="catalog-empty">
                <p className="empty">Nenhuma peça encontrada.</p>
                {suggestions.length > 0 && (
                  <div className="catalog-suggestions">
                    <p>Talvez seja uma destas peças?</p>
                    <div className="product-grid product-grid--suggestions">
                      {suggestions.map((product) => (
                        <ProductCard key={product.id} product={product} variant="catalog" />
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
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}

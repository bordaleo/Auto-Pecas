import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Car, ChevronRight, RotateCcw, Search, SlidersHorizontal, X } from 'lucide-react';
import { fetchCatalogFilters, productList, productCount, api } from '../api/client';
import ProductCard from '../components/ProductCard';
import VehicleFinder from '../components/VehicleFinder';
import { trackPopularClick, trackSearch } from '../utils/catalogAnalytics';

const DEBOUNCE_MS = 350;

const POPULAR_FALLBACK = [
  'Filtro de óleo VW/Audi',
  'Kit correia dentada Onix/Prisma',
  "Bomba d'água Ford Ka",
  'Alternador 90A Gol/Polo/Fox 1.0/1.6',
  'Fluido de freio DOT',
  'Amortecedor dianteiro Palio/Siena/Strada',
  'Disco de freio ventilado',
  'Pastilha de freio dianteira',
];

function resolvePopularTerms(apiList) {
  const fromApi = (apiList || [])
    .map((item) => (typeof item === 'string' ? item : item?.q || ''))
    .map((q) => q.trim())
    .filter((q) => q.length >= 3);

  if (fromApi.length >= 3) return fromApi.slice(0, 8);

  const seen = new Set(fromApi.map((t) => t.toLowerCase()));
  const merged = [...fromApi];
  for (const term of POPULAR_FALLBACK) {
    if (merged.length >= 8) break;
    if (!seen.has(term.toLowerCase())) {
      merged.push(term);
      seen.add(term.toLowerCase());
    }
  }
  return merged;
}

function buildQuery(filters, extra = {}) {
  const query = new URLSearchParams();
  Object.entries({ ...filters, ...extra }).forEach(([key, value]) => {
    if (value && key !== 'page') query.set(key, value);
  });
  if (extra.page && Number(extra.page) > 1) {
    query.set('page', String(extra.page));
  }
  return query;
}

function hasActiveFilters(filters) {
  return Boolean(
    filters.q || filters.category || filters.brand || filters.featured
    || filters.in_stock || filters.vehicle_brand || filters.vehicle_model || filters.vehicle_year,
  );
}

function filtersToDraft(searchParams) {
  return {
    q: searchParams.get('q') || '',
    category: searchParams.get('category') || '',
    brand: searchParams.get('brand') || '',
    featured: searchParams.get('featured') || '',
    in_stock: searchParams.get('in_stock') || '',
    vehicle_brand: searchParams.get('vehicle_brand') || '',
    vehicle_model: searchParams.get('vehicle_model') || '',
    vehicle_year: searchParams.get('vehicle_year') || '',
    ordering: searchParams.get('ordering') || '',
  };
}

export default function Catalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [vehicleBrands, setVehicleBrands] = useState([]);
  const [products, setProducts] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [count, setCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filtersLoading, setFiltersLoading] = useState(true);
  const [catalogError, setCatalogError] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [vehicleModelName, setVehicleModelName] = useState('');
  const [popularTerms, setPopularTerms] = useState([]);
  const debounceRef = useRef(null);
  const searchSourceRef = useRef('typed');
  const lastTrackedSearch = useRef('');

  const filters = useMemo(() => filtersToDraft(searchParams), [searchParams]);
  const page = Math.max(1, parseInt(searchParams.get('page') || '1', 10) || 1);

  const [draft, setDraft] = useState(filters);
  const [searchInput, setSearchInput] = useState(filters.q);

  const vehicleFilter = useMemo(() => ({
    vehicle_brand: filters.vehicle_brand,
    vehicle_model: filters.vehicle_model,
    vehicle_year: filters.vehicle_year,
  }), [filters.vehicle_brand, filters.vehicle_model, filters.vehicle_year]);

  const activeCategory = useMemo(
    () => categories.find((c) => c.slug === filters.category),
    [categories, filters.category],
  );

  useEffect(() => {
    setDraft(filters);
    setSearchInput(filters.q);
  }, [filters]);

  useEffect(() => {
    if (!filtersOpen) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [filtersOpen]);

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
    fetchCatalogFilters()
      .then((data) => {
        setCategories(productList(data.categories));
        setBrands(data.product_brands || []);
        setVehicleBrands(data.vehicle_brands || []);
        setPopularTerms(resolvePopularTerms(data.popular_searches));
      })
      .catch(() => api('/categories/').then((cats) => {
        setCategories(productList(cats));
        return Promise.all([api('/products/brands/'), api('/vehicles/brands/')]);
      }).then(([brandList, vBrands]) => {
        setBrands(brandList);
        setVehicleBrands(vBrands);
        setPopularTerms(resolvePopularTerms([]));
      }))
      .catch(() => {
        setCatalogError('Não foi possível carregar os filtros. Verifique se o servidor está online.');
      })
      .finally(() => setFiltersLoading(false));
  }, []);

  useEffect(() => {
    const isLoadMore = page > 1;
    if (isLoadMore) setLoadingMore(true);
    else setLoading(true);
    setCatalogError('');

    const query = buildQuery(filters, { page: page > 1 ? page : undefined });
    const path = `/products/${query.toString() ? `?${query}` : ''}`;

    let cancelled = false;
    api(path)
      .then((data) => {
        if (cancelled) return;
        const results = productList(data);
        const total = productCount(data, results);
        setCount(total);
        setHasMore(Boolean(data.next));

        if (isLoadMore) {
          setProducts((prev) => {
            const ids = new Set(prev.map((p) => p.id));
            return [...prev, ...results.filter((p) => !ids.has(p.id))];
          });
        } else {
          setProducts(results);
        }

        if (!isLoadMore && filters.q) {
          const trackKey = `${filters.q}|${JSON.stringify(vehicleFilter)}`;
          if (lastTrackedSearch.current !== trackKey) {
            lastTrackedSearch.current = trackKey;
            trackSearch(filters.q, { ...filters }, total, searchSourceRef.current);
          }
        }

        if (!results.length && !isLoadMore) {
          const sq = buildQuery(filters);
          api(`/part-requests/suggestions/${sq.toString() ? `?${sq}` : ''}`)
            .then((d) => { if (!cancelled) setSuggestions(d.products || []); })
            .catch(() => { if (!cancelled) setSuggestions([]); });
        } else if (!isLoadMore) {
          setSuggestions([]);
        }
      })
      .catch(() => {
        if (cancelled) return;
        if (!isLoadMore) {
          setProducts([]);
          setCount(0);
        }
        setCatalogError('Erro ao carregar peças. Confirme que o backend está rodando.');
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setLoadingMore(false);
        }
      });

    return () => { cancelled = true; };
  }, [filters, page, vehicleFilter]);

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

  const scheduleSearch = (value, source = 'typed') => {
    searchSourceRef.current = source;
    setSearchInput(value);
    setDraft((prev) => ({ ...prev, q: value }));
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.delete('page');
        if (value.trim()) next.set('q', value.trim());
        else next.delete('q');
        return next;
      });
    }, DEBOUNCE_MS);
  };

  const submitSearch = (event) => {
    event.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    searchSourceRef.current = 'typed';
    const value = searchInput.trim();
    setDraft((prev) => ({ ...prev, q: value }));
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('page');
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

  const clearSearchOnly = () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setSearchInput('');
    const next = { ...draft, q: '' };
    setDraft(next);
    pushFilters(next);
  };

  const clearVehicleOnly = () => {
    const next = {
      ...draft,
      vehicle_brand: '',
      vehicle_model: '',
      vehicle_year: '',
    };
    setVehicleModelName('');
    setDraft(next);
    pushFilters(next);
    setFiltersOpen(true);
  };

  const removeFilter = (key) => {
    if (key === 'vehicle') {
      const next = {
        ...draft,
        vehicle_brand: '',
        vehicle_model: '',
        vehicle_year: '',
      };
      setVehicleModelName('');
      setDraft(next);
      pushFilters(next);
      return;
    }

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
    if (patch.q !== undefined) setSearchInput(patch.q || '');

    setDraft((prev) => {
      const { vehicle_model_name, ...rest } = patch;
      const merged = { ...prev, ...rest };
      if (patch.q) {
        setSearchInput(patch.q || '');
        pushFilters(merged);
      }
      return merged;
    });
  };

  const applyVehicleSelection = (vehiclePatch) => {
    const { vehicle_model_name, ...rest } = vehiclePatch;
    if (vehicle_model_name !== undefined) {
      setVehicleModelName(vehicle_model_name || '');
    }
    setDraft((prev) => {
      const merged = { ...prev, ...rest };
      pushFilters(merged);
      return merged;
    });
    if (rest.q !== undefined) setSearchInput(rest.q || '');
  };

  const loadMore = useCallback(() => {
    if (loadingMore || !hasMore) return;
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      const current = parseInt(next.get('page') || '1', 10) || 1;
      next.set('page', String(current + 1));
      return next;
    });
  }, [hasMore, loadingMore, setSearchParams]);

  const applyCategory = (slug) => {
    const next = { ...draft, category: slug };
    setDraft(next);
    pushFilters(next);
  };

  const handlePopularClick = (term, isActive) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    searchSourceRef.current = 'popular';
    const value = isActive ? '' : term;
    if (!isActive) trackPopularClick(term, { ...filters });
    setSearchInput(value);
    const next = { ...draft, q: value };
    if (value) next.category = '';
    setDraft(next);
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.delete('page');
      if (value.trim()) {
        params.set('q', value.trim());
        params.delete('category');
      } else {
        params.delete('q');
      }
      return params;
    });
  };

  const filterChips = useMemo(() => {
    const parts = [];
    const other = [];

    let vehicleSummary = null;
    if (filters.vehicle_brand || filters.vehicle_model || filters.vehicle_year) {
      const vb = vehicleBrands.find((b) => b.slug === filters.vehicle_brand);
      const modelLabel = vehicleModelName
        || (filters.vehicle_model ? filters.vehicle_model.replace(/-/g, ' ') : '');
      vehicleSummary = [
        vb?.name,
        modelLabel,
        filters.vehicle_year ? `Ano ${filters.vehicle_year}` : null,
      ].filter(Boolean).join(' · ');
    }

    if (filters.q) parts.push({ key: 'q', label: filters.q, group: 'parts' });
    if (filters.category) {
      parts.push({ key: 'category', label: activeCategory?.name || filters.category, group: 'parts' });
    }
    if (filters.brand) parts.push({ key: 'brand', label: filters.brand, group: 'parts' });
    if (filters.in_stock) other.push({ key: 'in_stock', label: 'Em estoque', group: 'other' });
    if (filters.featured) other.push({ key: 'featured', label: 'Destaques', group: 'other' });

    const all = [
      ...(vehicleSummary ? [{ key: 'vehicle', label: vehicleSummary, group: 'vehicle' }] : []),
      ...parts,
      ...other,
    ];

    return { vehicleSummary, parts, other, all };
  }, [filters, activeCategory, vehicleBrands, vehicleModelName]);

  const relatedCategories = useMemo(() => {
    if (loading || products.length > 0 || filters.q) return [];
    const withStock = categories.filter((c) => (c.product_count ?? 0) > 0);
    if (filters.category) {
      return withStock.filter((c) => c.slug !== filters.category).slice(0, 5);
    }
    return withStock.slice(0, 5);
  }, [loading, products.length, filters.q, filters.category, categories]);

  const hasTextSearch = Boolean(filters.q?.trim());
  const showDiscovery = !hasTextSearch;
  const showEmpty = !loading && !products.length;
  const showClearAll = filterChips.all.length >= 2;
  const showPopularSearches = showDiscovery && popularTerms.length > 0;
  const showEmptyDiscovery = showEmpty && showDiscovery;
  const showEmptySearched = showEmpty && hasTextSearch;

  const sidebarContent = (
    <>
      <VehicleFinder
        brands={vehicleBrands}
        brand={draft.vehicle_brand}
        modelSlug={draft.vehicle_model}
        year={draft.vehicle_year}
        onChange={handleVehicleChange}
        onApply={applyVehicleSelection}
        onApplyFilters={applyFilters}
        onClearFilters={clearFilters}
        showClearFilters={hasActiveFilters(filters)}
        disabled={filtersLoading}
      />

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
            <label className="filter-checkbox" htmlFor="filter-in-stock">
              <input
                id="filter-in-stock"
                type="checkbox"
                checked={!!draft.in_stock}
                onChange={(e) => setDraft({ ...draft, in_stock: e.target.checked ? '1' : '' })}
                disabled={filtersLoading}
              />
              <span>Somente em estoque</span>
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
    </>
  );

  return (
    <div className="catalog-page">
      <header className="catalog-hero wrap">
        <nav className="catalog-breadcrumbs" aria-label="Navegação">
          <Link to="/pecas">Catálogo</Link>
          {activeCategory && (
            <>
              <ChevronRight size={14} aria-hidden="true" />
              <span aria-current="page">{activeCategory.name}</span>
            </>
          )}
          {!activeCategory && filters.q && (
            <>
              <ChevronRight size={14} aria-hidden="true" />
              <span aria-current="page">{filters.q}</span>
            </>
          )}
        </nav>

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
            onChange={(e) => scheduleSearch(e.target.value, 'typed')}
            aria-label="Buscar peças"
          />
          {searchInput && (
            <button
              type="button"
              className="catalog-search__clear"
              onClick={() => scheduleSearch('', 'typed')}
              aria-label="Limpar busca"
            >
              <X size={16} />
            </button>
          )}
          <button type="submit" className="btn btn-accent catalog-search__btn">
            Buscar
          </button>
        </form>

        {filterChips.all.length > 0 && (
          <div className="catalog-filters-bar">
            <div className="catalog-filters-bar__chips">
              {filterChips.all.map((chip) => (
                <button
                  key={chip.key}
                  type="button"
                  className={`catalog-filters-bar__chip${chip.group === 'vehicle' ? ' catalog-filters-bar__chip--vehicle' : ''}`}
                  onClick={() => removeFilter(chip.key)}
                  title="Remover filtro"
                >
                  {chip.group === 'vehicle' && <Car size={15} aria-hidden="true" />}
                  <span>{chip.label}</span>
                  <X size={14} aria-hidden="true" />
                </button>
              ))}
            </div>
            {showClearAll && (
              <button type="button" className="catalog-filters-bar__clear" onClick={clearFilters}>
                Limpar tudo
              </button>
            )}
          </div>
        )}

        {catalogError && (
          <div className="catalog-alert catalog-alert--error" role="alert">
            {catalogError}
          </div>
        )}
      </header>

      <div className="wrap catalog-layout">
        {filtersOpen && (
          <button
            type="button"
            className="catalog-drawer-backdrop"
            onClick={() => setFiltersOpen(false)}
            aria-label="Fechar filtros"
          />
        )}

        <aside className={`filters-panel${filtersOpen ? ' is-open' : ''}`}>
          <div className="catalog-drawer__head">
            <h2>Filtros</h2>
            <button
              type="button"
              className="catalog-drawer__close"
              onClick={() => setFiltersOpen(false)}
              aria-label="Fechar filtros"
            >
              <X size={20} />
            </button>
          </div>
          {sidebarContent}
        </aside>

        <section className="catalog-results">
          {showPopularSearches && (
            <div className="catalog-popular">
              <p className="catalog-popular__title">Buscas populares</p>
              <p className="catalog-popular__subtitle">O que mais procuram no catálogo</p>
              <div className="catalog-popular__list" role="list">
                {popularTerms.map((term) => {
                  const isActive = filters.q.toLowerCase() === term.toLowerCase();
                  return (
                    <button
                      key={term}
                      type="button"
                      role="listitem"
                      className={`catalog-popular__term${isActive ? ' is-active' : ''}`}
                      onClick={() => handlePopularClick(term, isActive)}
                      aria-pressed={isActive}
                    >
                      <Search size={14} aria-hidden="true" />
                      {term}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div className="catalog-toolbar">
            <span className={`catalog-toolbar-status${loading ? ' is-loading' : ''}`}>
              {loading ? 'Carregando peças...' : `${count} resultado(s)`}
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
            {products.length ? (
              products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  variant="catalog"
                  vehicleFilter={vehicleFilter}
                />
              ))
            ) : showEmpty ? (
              <div className={`catalog-empty${showEmptySearched ? ' catalog-empty--searched' : ''}${showEmptyDiscovery ? ' catalog-empty--discovery' : ''}`}>
                {showEmptySearched ? (
                  <>
                    <div className="catalog-empty__icon" aria-hidden="true">
                      <Search size={28} />
                    </div>
                    <h2 className="catalog-empty__title">Nenhum resultado encontrado</h2>
                    <p className="catalog-empty__lead">
                      Não encontramos peças para <strong>&ldquo;{filters.q}&rdquo;</strong>.
                      Tente outro termo ou sinônimo.
                    </p>
                    <div className="catalog-empty__actions catalog-empty__actions--compact">
                      <button type="button" className="btn btn-primary" onClick={clearSearchOnly}>
                        <RotateCcw size={16} aria-hidden="true" />
                        Limpar busca
                      </button>
                      {hasActiveFilters(filters) && (
                        <button type="button" className="btn btn-secondary" onClick={clearFilters}>
                          Limpar filtros
                        </button>
                      )}
                    </div>
                  </>
                ) : showEmptyDiscovery ? (
                  <div className="catalog-empty__body">
                    <div className="catalog-empty__icon" aria-hidden="true">
                      <Search size={28} />
                    </div>
                    <h2 className="catalog-empty__title">Nenhuma peça encontrada</h2>
                    <p className="catalog-empty__lead">
                      Ajuste os filtros ou explore por categoria abaixo.
                    </p>

                    <div className="catalog-empty__actions">
                      {hasActiveFilters(filters) && (
                        <button type="button" className="catalog-empty__action" onClick={clearFilters}>
                          <RotateCcw size={18} aria-hidden="true" />
                          <span>Limpar filtros</span>
                        </button>
                      )}
                      {(filters.vehicle_brand || filters.vehicle_model) && (
                        <button type="button" className="catalog-empty__action" onClick={clearVehicleOnly}>
                          <Car size={18} aria-hidden="true" />
                          <span>Trocar veículo</span>
                        </button>
                      )}
                      <button
                        type="button"
                        className="catalog-empty__action catalog-filters-toggle"
                        onClick={() => setFiltersOpen(true)}
                      >
                        <SlidersHorizontal size={18} aria-hidden="true" />
                        <span>Abrir filtros</span>
                      </button>
                    </div>

                    {relatedCategories.length > 0 && (
                      <div className="catalog-discovery catalog-discovery--categories">
                        <p className="catalog-discovery__title">Categorias para explorar</p>
                        <div className="catalog-discovery__cats" role="list">
                          {relatedCategories.map((cat) => (
                            <button
                              key={cat.slug}
                              type="button"
                              role="listitem"
                              className="catalog-discovery__cat"
                              onClick={() => applyCategory(cat.slug)}
                            >
                              <span className="catalog-discovery__cat-icon" aria-hidden="true">
                                {cat.icon || '📦'}
                              </span>
                              <span className="catalog-discovery__cat-name">{cat.name}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}

                {suggestions.length > 0 && (
                  <div className="catalog-suggestions">
                    <p>Talvez seja uma destas peças?</p>
                    <div className="product-grid product-grid--suggestions">
                      {suggestions.map((product) => (
                        <ProductCard
                          key={product.id}
                          product={product}
                          variant="catalog"
                          vehicleFilter={vehicleFilter}
                        />
                      ))}
                    </div>
                  </div>
                )}

                <p className="catalog-empty__footer">
                  Não achou o que precisa? Publique um pedido e receba contato de vendedores.
                </p>
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

          {hasMore && products.length > 0 && (
            <div className="catalog-load-more">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={loadMore}
                disabled={loadingMore}
              >
                {loadingMore ? 'Carregando...' : `Carregar mais (${products.length} de ${count})`}
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

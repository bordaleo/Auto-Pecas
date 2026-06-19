import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, productCount, productList } from '../api/client';
import ProductCard from '../components/ProductCard';

export default function Catalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [products, setProducts] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState('');

  const filters = useMemo(() => ({
    q: searchParams.get('q') || '',
    category: searchParams.get('category') || '',
    brand: searchParams.get('brand') || '',
    featured: searchParams.get('featured') || '',
    in_stock: searchParams.get('in_stock') || '',
  }), [searchParams]);

  const [draft, setDraft] = useState(filters);

  useEffect(() => {
    setDraft(filters);
  }, [filters]);

  useEffect(() => {
    Promise.all([api('/categories/'), api('/products/brands/')])
      .then(([cats, brandList]) => {
        setCategories(productList(cats));
        setBrands(brandList);
      })
      .catch(() => {});
  }, []);

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
    setSearchParams(next);
  };

  return (
    <div className="wrap catalog-layout">
      <aside className="filters-panel">
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

import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, productCount, productList } from '../api/client';
import { useStore } from '../context/StoreContext';
import HomeHeroZone from '../components/HomeHeroZone';
import BrandMarquee from '../components/BrandMarquee';
import ProductCard from '../components/ProductCard';
import ProductGridSkeleton from '../components/ProductGridSkeleton';
import SectionHeader from '../components/SectionHeader';
import HeroSection from '../components/landing/HeroSection';
import CategoriesSection from '../components/landing/CategoriesSection';
import WhyUsSection from '../components/landing/WhyUsSection';
import TrustSection from '../components/landing/TrustSection';
import CtaSection from '../components/landing/CtaSection';

export default function Home() {
  const navigate = useNavigate();
  const { config } = useStore();
  const [featured, setFeatured] = useState([]);
  const [popular, setPopular] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [featuredLoading, setFeaturedLoading] = useState(true);
  const [popularLoading, setPopularLoading] = useState(true);
  const [catalogError, setCatalogError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setCatalogError(false);
    setFeaturedLoading(true);
    setPopularLoading(true);

    api('/products/?featured=1&page_size=8')
      .then((data) => {
        if (cancelled) return;
        setFeatured(productList(data).slice(0, 8));
      })
      .catch(() => {
        if (!cancelled) setCatalogError(true);
      })
      .finally(() => {
        if (!cancelled) setFeaturedLoading(false);
      });

    api('/products/?page_size=8')
      .then((data) => {
        if (cancelled) return;
        const list = productList(data);
        setPopular(list.slice(0, 8));
        setTotalProducts(productCount(data, list));
      })
      .catch(() => {
        if (!cancelled) setCatalogError(true);
      })
      .finally(() => {
        if (!cancelled) setPopularLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  const handleSearch = (query) => {
    navigate(`/pecas/?q=${encodeURIComponent(query)}`);
  };

  return (
    <div className="home home--enhanced">
      <HomeHeroZone onSearch={handleSearch} />
      <HeroSection />
      <BrandMarquee />
      <CategoriesSection />
      <WhyUsSection />

      {catalogError && (
        <p className="state-empty wrap" style={{ marginTop: '1rem' }}>
          Não foi possível carregar o catálogo. Verifique se o backend está rodando
          {' '}(<code>python manage.py runserver</code> ou <code>npm run dev:backend</code>).
        </p>
      )}

      <section className="home-section wrap">
        <SectionHeader
          title="Seleção em destaque"
          subtitle={totalProducts > 0 ? `${totalProducts} peças no catálogo Galelugi` : 'Ofertas selecionadas'}
          href="/pecas/?featured=1"
          linkLabel="Ver todos"
        />
        {featuredLoading ? (
          <ProductGridSkeleton count={8} />
        ) : featured.length ? (
          <div className="product-grid">
            {featured.map((product) => <ProductCard key={product.id} product={product} />)}
          </div>
        ) : (
          <p className="state-empty">Nenhum destaque ainda. <Link to="/pecas/">Ver catálogo</Link></p>
        )}
      </section>

      <TrustSection />

      <section className="promo-band wrap">
        <div className="promo-band__card">
          <div className="promo-band__content">
            <span className="promo-band__eyebrow">Para vendedores</span>
            <h3>Tem peças para vender? Abra sua loja na Galelugi</h3>
            <p>
              Publique anúncios, alcance compradores em todo o Brasil e receba o repasse após cada venda.
              Comissão de {config.marketplace_commission_percent || 8}% por transação.
            </p>
          </div>
          <div className="promo-band__actions">
            <Link to="/como-funciona/" className="gl-btn gl-btn--ghost">Como funciona</Link>
            <Link to="/vender/" className="gl-btn gl-btn--primary">Começar a vender</Link>
          </div>
        </div>
      </section>

      <CtaSection />

      <section className="home-section wrap">
        <SectionHeader
          title="Mais procuradas"
          subtitle="Peças que nossos clientes buscam com frequência"
          href="/pecas/"
        />
        {popularLoading ? (
          <ProductGridSkeleton count={8} />
        ) : (
          <div className="product-grid">
            {popular.map((product) => (
              <ProductCard key={`pop-${product.id}`} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

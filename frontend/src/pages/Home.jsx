import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, productCount, productList } from '../api/client';
import { useStore } from '../context/StoreContext';
import CouponBanner from '../components/CouponBanner';
import BrandMarquee from '../components/BrandMarquee';
import HeroBanner from '../components/HeroBanner';
import ProductCard from '../components/ProductCard';
import SectionHeader from '../components/SectionHeader';
import ValuePillars from '../components/ValuePillars';

const CAT_COLORS = ['#D4622A', '#3D8B7A', '#5B7DB1', '#8B5E3C', '#6B4C9A', '#C45B28'];

export default function Home() {
  const { categories, config } = useStore();
  const [featured, setFeatured] = useState([]);
  const [popular, setPopular] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);

  useEffect(() => {
    Promise.all([
      api('/products/?featured=1'),
      api('/products/'),
    ]).then(([featuredData, allData]) => {
      const all = productList(allData);
      setFeatured(productList(featuredData).slice(0, 8));
      setPopular(all.slice(0, 8));
      setTotalProducts(productCount(allData, all));
    }).catch(() => {});
  }, []);

  return (
    <div className="home">
      <CouponBanner />
      <HeroBanner />
      <ValuePillars />

      <section className="home-section wrap">
        <SectionHeader
          title="Departamentos"
          subtitle="Navegue por tipo de componente"
          href="/pecas/"
        />
        <div className="dept-grid">
          {categories.map((cat, i) => (
            <Link
              key={cat.slug}
              to={`/pecas/?category=${cat.slug}`}
              className="dept-card"
              style={{ '--dept-color': CAT_COLORS[i % CAT_COLORS.length] }}
            >
              <span className="dept-icon">{cat.icon || '⚙'}</span>
              <span className="dept-name">{cat.name}</span>
              <span className="dept-arrow">→</span>
            </Link>
          ))}
        </div>
      </section>

      <BrandMarquee />

      <section className="home-section wrap">
        <SectionHeader
          title="Seleção em destaque"
          subtitle={totalProducts > 0 ? `${totalProducts} peças no catálogo Galelugi` : 'Ofertas selecionadas'}
          href="/pecas/?featured=1"
          linkLabel="Ver todos"
        />
        <div className="product-grid">
          {featured.length ? (
            featured.map((product) => <ProductCard key={product.id} product={product} />)
          ) : (
            <p className="state-empty">Nenhum destaque ainda. <Link to="/pecas/">Ver catálogo</Link></p>
          )}
        </div>
      </section>

      <section className="trust-banner wrap">
        <div className="trust-banner-inner">
          <div>
            <span className="eyebrow eyebrow--light">Galelugi Garante</span>
            <h3>Estoque real. Peça certa. Entrega que funciona.</h3>
            <p>
              Frete grátis em pedidos acima de R$ {config.free_shipping_min || 299}.
              Retirada na loja disponível. Pagamento seguro via Mercado Pago.
            </p>
          </div>
          <Link to="/pecas/" className="btn btn-light">Comprar agora</Link>
        </div>
      </section>

      <section className="trust-banner wrap">
        <div className="trust-banner-inner">
          <div>
            <span className="eyebrow eyebrow--light">Para vendedores</span>
            <h3>Tem peças para vender? Abra sua loja na Galelugi</h3>
            <p>
              Publique anúncios, alcance compradores em todo o Brasil e receba o repasse após cada venda.
              Comissão de {config.marketplace_commission_percent || 8}% por transação.
            </p>
          </div>
            <Link to="/como-funciona/" className="btn btn-secondary" style={{ marginRight: '0.5rem' }}>Como funciona</Link>
          <Link to="/vender/" className="btn btn-light">Começar a vender</Link>
        </div>
      </section>

      <section className="home-section wrap">
        <SectionHeader
          title="Mais procuradas"
          subtitle="Peças que nossos clientes buscam com frequência"
          href="/pecas/"
        />
        <div className="product-grid">
          {popular.map((product) => (
            <ProductCard key={`pop-${product.id}`} product={product} />
          ))}
        </div>
      </section>
    </div>
  );
}

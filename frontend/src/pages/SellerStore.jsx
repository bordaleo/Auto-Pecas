import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import ProductCard from '../components/ProductCard';
import PageLoader from '../components/ui/PageLoader';
import SectionHeader from '../components/SectionHeader';

export default function SellerStore() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    api(`/seller/store/${slug}/`)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setNotFound(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [slug]);

  if (loading) {
    return (
      <div className="wrap home-section" style={{ marginTop: '1.25rem' }}>
        <PageLoader label="Carregando loja..." />
      </div>
    );
  }

  if (notFound || !data) {
    return <div className="wrap"><p className="state-empty">Loja não encontrada.</p></div>;
  }

  const { seller, products } = data;

  return (
    <div className="wrap home-section" style={{ marginTop: '1.25rem' }}>
      <div className="seller-store-head">
        <span className="eyebrow">{seller.is_official ? 'Loja oficial' : 'Loja parceira'}</span>
        <h1>
          {seller.store_name}
          {seller.is_official && <span className="store-badge store-badge--lg">Oficial</span>}
        </h1>
        {seller.description && <p>{seller.description}</p>}
        {seller.ships_from_platform && (
          <p className="seller-store-ship-note">Envio realizado pela Auto Peças Sandroni</p>
        )}
      </div>
      <SectionHeader title="Peças desta loja" />
      <div className="product-grid">
        {products.length ? (
          products.map((product) => <ProductCard key={product.id} product={product} />)
        ) : (
          <p className="state-empty">Esta loja ainda não publicou peças.</p>
        )}
      </div>
      <Link to="/pecas/" className="btn btn-secondary" style={{ marginTop: '1.5rem' }}>Ver catálogo completo</Link>
    </div>
  );
}

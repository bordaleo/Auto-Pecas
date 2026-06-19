import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import ProductCard from '../components/ProductCard';
import SectionHeader from '../components/SectionHeader';

export default function SellerStore() {
  const { slug } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => {
    api(`/seller/store/${slug}/`).then(setData).catch(() => setData(null));
  }, [slug]);

  if (!data) {
    return <div className="wrap"><p className="state-empty">Loja não encontrada.</p></div>;
  }

  const { seller, products } = data;

  return (
    <div className="wrap home-section" style={{ marginTop: '1.25rem' }}>
      <div className="seller-store-head">
        <span className="eyebrow">Loja parceira</span>
        <h1>{seller.store_name}</h1>
        {seller.description && <p>{seller.description}</p>}
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

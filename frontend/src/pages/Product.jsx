import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, buildWhatsAppProductUrl, formatCurrency } from '../api/client';
import { calcInstallment } from '../utils/commerce';
import { getSavedZip, saveZip } from '../components/ProductCard';
import ProductReviews from '../components/ProductReviews';
import ProductChat from '../components/ProductChat';
import PageSeo from '../components/PageSeo';
import PageLoader from '../components/ui/PageLoader';
import { useCart } from '../context/CartContext';
import { useStore } from '../context/StoreContext';
import { useToast } from '../context/ToastContext';

export default function Product() {
  const { slug } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [qty, setQty] = useState(1);
  const [mainImage, setMainImage] = useState('');
  const [zip, setZip] = useState(getSavedZip());
  const [shippingLabel, setShippingLabel] = useState('');
  const { addItem } = useCart();
  const { showToast } = useToast();
  const { config, whatsappUrl } = useStore();

  useEffect(() => {
    setLoading(true);
    setNotFound(false);
    setProduct(null);
    setQty(1);
    api(`/products/${slug}/`)
      .then((data) => {
        setProduct(data);
        const images = [data.image_url, ...(data.images || []).map((img) => img.url)].filter(Boolean);
        setMainImage(images[0] || '');
      })
      .catch(() => {
        setProduct(null);
        setNotFound(true);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  useEffect(() => {
    if (!product) return;
    const digits = zip.replace(/\D/g, '');
    if (digits.length < 8) {
      const freeMin = Number(config.free_shipping_min || 299);
      const qualifies = Number(product.price) >= freeMin;
      setShippingLabel(qualifies ? 'Frete grátis para este produto' : `Frete grátis acima de ${formatCurrency(freeMin)}`);
      return;
    }
    api('/shop/shipping/quote/', {
      method: 'POST',
      body: JSON.stringify({
        delivery_method: 'delivery',
        shipping_zip: digits,
        subtotal: product.price,
      }),
    })
      .then((quote) => {
        const fee = parseFloat(quote.shipping_fee) || 0;
        setShippingLabel(fee === 0 ? 'Frete grátis para seu CEP' : `Frete: ${formatCurrency(fee)}`);
      })
      .catch(() => setShippingLabel('Informe um CEP válido'));
  }, [product, zip, config.free_shipping_min]);

  if (loading) {
    return <PageLoader label="Carregando peça..." />;
  }

  if (notFound || !product) {
    return (
      <div className="wrap">
        <p className="empty">Peça não encontrada. <Link to="/pecas/">Ver catálogo</Link></p>
      </div>
    );
  }

  const images = [product.image_url, ...(product.images || []).map((img) => img.url)].filter(Boolean);
  const inStock = product.in_stock !== false && product.stock > 0;
  const freeMin = Number(config.free_shipping_min || 299);
  const waUrl = buildWhatsAppProductUrl(whatsappUrl, product);

  const handleAdd = () => {
    addItem(product, qty);
  };

  const quoteZip = () => {
    saveZip(zip);
    showToast('CEP salvo para estimativa de frete');
  };

  return (
    <>
      <PageSeo
        title={product.seo_title || `${product.name} | Galelugi Peças`}
        description={product.seo_description || product.description}
        image={mainImage || product.image_url}
        canonical={`${window.location.origin}/peca/${product.slug}/`}
      />
      <div className="wrap product-layout">
      <div>
        <div className="gallery-main">
          {mainImage ? (
            <img src={mainImage} alt={product.name} />
          ) : (
            <span className="ph" style={{ fontSize: '4rem', opacity: 0.2 }}>⚙</span>
          )}
        </div>
        {images.length > 1 && (
          <div className="gallery-thumbs">
            {images.map((url) => (
              <img
                key={url}
                src={url}
                alt=""
                className={url === mainImage ? 'active' : ''}
                onClick={() => setMainImage(url)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="product-info">
        {product.seller_name && (
          <p className="product-seller">
            Vendido por{' '}
            <Link to={`/loja/${product.seller_slug}/`}>{product.seller_name}</Link>
          </p>
        )}

        <h1>{product.name}</h1>

        <div className="part-badges">
          {product.part_condition && (
            <span className="part-badge">
              {{ new: 'Nova', used: 'Usada', reconditioned: 'Recondicionada' }[product.part_condition] || product.part_condition}
            </span>
          )}
          {product.part_origin && (
            <span className="part-badge">
              {{ original: 'Original', parallel: 'Paralela', remanufactured: 'Remanufaturada' }[product.part_origin] || product.part_origin}
            </span>
          )}
          {product.warranty_days > 0 && (
            <span className="part-badge">Garantia {product.warranty_days} dias</span>
          )}
        </div>

        {(product.brand || product.category || product.sku || product.oem_code) && (
          <dl className="product-specs">
            {product.brand && (
              <div className="product-spec">
                <dt>Marca</dt>
                <dd>{product.brand}</dd>
              </div>
            )}
            {product.category && (
              <div className="product-spec">
                <dt>Categoria</dt>
                <dd>{product.category.name}</dd>
              </div>
            )}
            {product.sku && (
              <div className="product-spec">
                <dt>SKU</dt>
                <dd>{product.sku}</dd>
              </div>
            )}
            {product.oem_code && (
              <div className="product-spec">
                <dt>OEM</dt>
                <dd>{product.oem_code}</dd>
              </div>
            )}
          </dl>
        )}

        <div className="product-price-block">
          <div className="product-price">{formatCurrency(product.price)}</div>
          <div className="product-promo-banner">
            <span>em <strong>12x {calcInstallment(product.price)}</strong> sem juros</span>
            {Number(product.price) >= freeMin && <span className="product-free-ship">Frete grátis</span>}
          </div>
          <span className={inStock ? 'gl-card-stock' : 'gl-card-oos'}>
            {inStock ? `${product.available_stock ?? product.stock} un. em estoque` : 'Indisponível'}
          </span>
          {(product.average_rating > 0) && (
            <p className="product-rating">★ {product.average_rating} ({product.review_count} avaliações)</p>
          )}
        </div>

        <div className="product-buy-block">
          <div className="qty-row">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setQty(Math.max(1, qty - 1))}>−</button>
            <input value={qty} readOnly />
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setQty(Math.min(product.stock || 99, qty + 1))}>+</button>
            <button type="button" className="btn btn-primary" onClick={handleAdd} disabled={!inStock}>
              Comprar agora
            </button>
          </div>
        </div>

        <div className="product-shipping-box">
          <label>Calcule o frete pelo CEP</label>
          <div className="product-shipping-row">
            <input
              value={zip}
              onChange={(e) => setZip(e.target.value)}
              placeholder="00000-000"
              maxLength={9}
            />
            <button type="button" className="btn btn-secondary btn-sm" onClick={quoteZip}>Calcular</button>
          </div>
          <p className="product-shipping-result">{shippingLabel}</p>
        </div>

        <a href={waUrl} className="btn btn-whatsapp btn-full" target="_blank" rel="noreferrer">
          Dúvida sobre compatibilidade? WhatsApp
        </a>

        <div className="product-section">
          <h2 className="product-section-title">Descrição</h2>
          <p className="product-section-text">
            {product.description || 'Peça automotiva Galelugi Peças.'}
          </p>
        </div>

        {product.vehicle_models?.length > 0 && (
          <div className="product-section product-section--box">
            <h2 className="product-section-title">Veículos compatíveis</h2>
            <ul className="product-compat-list">
              {product.vehicle_models.map((v) => (
                <li key={`${v.id}-${v.compat_year_start ?? 'a'}-${v.compat_year_end ?? 'a'}`}>
                  {v.brand} {v.name}
                  {v.compat_year_start != null
                    ? ` (${v.compat_year_start === v.compat_year_end ? v.compat_year_start : `${v.compat_year_start}-${v.compat_year_end}`})`
                    : ` (${v.year_start}-${v.year_end})`}
                </li>
              ))}
            </ul>
          </div>
        )}
        {product.compatible_vehicles && !product.vehicle_models?.length && (
          <div className="product-section product-section--box">
            <h2 className="product-section-title">Compatível</h2>
            <p className="product-section-text">{product.compatible_vehicles}</p>
          </div>
        )}

        <ProductChat product={product} />
      </div>
    </div>
    <div className="wrap product-reviews-wrap">
      <ProductReviews productId={product.id} />
    </div>
    </>
  );
}

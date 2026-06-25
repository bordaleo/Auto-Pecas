import { Link } from 'react-router-dom';
import { Star, Store, Truck, BadgeCheck } from 'lucide-react';
import { formatCurrency } from '../api/client';
import ProductImage from './ProductImage';
import { useStore } from '../context/StoreContext';
import { calcDiscount, calcInstallment } from '../utils/commerce';

const CONDITION_LABELS = { new: 'Nova', used: 'Usada', reconditioned: 'Recondicionada' };
const ORIGIN_LABELS = { original: 'OEM', parallel: 'Paralela', remanufactured: 'Remanuf.' };

const ZIP_KEY = 'galelugi_zip';

export function getSavedZip() {
  try {
    return localStorage.getItem(ZIP_KEY) || '';
  } catch {
    return '';
  }
}

export function saveZip(zip) {
  try {
    localStorage.setItem(ZIP_KEY, zip);
  } catch {
    /* ignore */
  }
}

function sellerInitials(name) {
  return (name || 'L')
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

export default function ProductCard({ product, shippingHint, variant = 'default' }) {
  const { config } = useStore();
  const isCatalog = variant === 'catalog';
  const inStock = product.in_stock !== false && product.stock > 0;
  const discount = calcDiscount(product.price, product.compare_at_price);
  const freeShipping = Number(product.price) >= Number(config.free_shipping_min || 299);
  const installment = calcInstallment(product.price);
  const sellerName = product.seller_name || 'Galelugi Peças';
  const hasRating = product.review_count > 0 && product.average_rating;

  const vendorStrip = (product.seller_name || product.seller_is_official || isCatalog) && (
    <div className="gl-card-vendor">
      <div className="gl-card-vendor__avatar" aria-hidden="true">
        {sellerInitials(sellerName)}
      </div>
      <div className="gl-card-vendor__body">
        <span className="gl-card-vendor__label">Vendido por</span>
        {product.seller_slug ? (
          <Link to={`/loja/${product.seller_slug}/`} className="gl-card-vendor__name">
            {sellerName}
          </Link>
        ) : (
          <span className="gl-card-vendor__name">{sellerName}</span>
        )}
      </div>
      <div className="gl-card-vendor__badges">
        {product.seller_is_official && (
          <span className="gl-card-vendor__badge gl-card-vendor__badge--official">
            <BadgeCheck size={12} aria-hidden="true" />
            Oficial
          </span>
        )}
        {product.seller_ships_from_platform && !product.seller_is_official && (
          <span className="gl-card-vendor__badge">
            <Truck size={12} aria-hidden="true" />
            Envio Galelugi
          </span>
        )}
      </div>
    </div>
  );

  return (
    <article className={`gl-card${isCatalog ? ' gl-card--catalog' : ''}`}>
      {isCatalog && vendorStrip}

      <Link to={`/peca/${product.slug}/`} className="gl-card-media">
        {discount > 0 && <span className="gl-card-tag gl-card-tag--discount">-{discount}%</span>}
        {product.is_featured && <span className="gl-card-tag gl-card-tag--hot">Destaque</span>}
        {!isCatalog && product.part_condition && (
          <span className="gl-card-tag gl-card-tag--cond">
            {CONDITION_LABELS[product.part_condition] || product.part_condition}
          </span>
        )}
        <ProductImage
          src={product.image_url}
          alt={product.name}
          categorySlug={product.category_slug}
          size="card"
        />
      </Link>

      <div className="gl-card-body">
        <div className="gl-card-meta">
          {product.category_name && (
            <span className="gl-card-category">{product.category_name}</span>
          )}
          {product.brand && <span className="gl-card-brand">{product.brand}</span>}
        </div>

        <h3 className="gl-card-title">
          <Link to={`/peca/${product.slug}/`}>{product.name}</Link>
        </h3>

        {isCatalog && product.oem_code && (
          <p className="gl-card-oem">OEM {product.oem_code}</p>
        )}

        {hasRating && (
          <div className="gl-card-rating" aria-label={`Nota ${product.average_rating} de 5`}>
            <Star size={13} fill="currentColor" aria-hidden="true" />
            <strong>{Number(product.average_rating).toFixed(1)}</strong>
            <span>({product.review_count})</span>
          </div>
        )}

        <div className="gl-card-price-block">
          {product.compare_at_price && (
            <span className="gl-card-old">{formatCurrency(product.compare_at_price)}</span>
          )}
          <span className="gl-card-price">{formatCurrency(product.price)}</span>
          <span className="gl-card-installment">
            ou <strong>12x {installment}</strong> sem juros
          </span>
        </div>

        <div className="gl-card-badges-row">
          {inStock ? (
            <span className="gl-card-pill gl-card-pill--stock">Em estoque</span>
          ) : (
            <span className="gl-card-pill gl-card-pill--oos">Indisponível</span>
          )}
          {freeShipping && (
            <span className="gl-card-pill gl-card-pill--ship">Frete grátis</span>
          )}
          {product.part_condition && isCatalog && (
            <span className="gl-card-pill">{CONDITION_LABELS[product.part_condition] || product.part_condition}</span>
          )}
          {product.part_origin && product.part_origin !== 'original' && (
            <span className="gl-card-pill">{ORIGIN_LABELS[product.part_origin] || product.part_origin}</span>
          )}
        </div>

        {shippingHint && <div className="gl-card-cep-hint">{shippingHint}</div>}

        {!isCatalog && (
          <div className="gl-card-foot">
            {(product.seller_name || product.seller_is_official) && (
              <div className="gl-card-seller-row">
                <Store size={12} aria-hidden="true" />
                {product.seller_slug ? (
                  <Link to={`/loja/${product.seller_slug}/`} className="gl-card-seller">
                    {sellerName}
                  </Link>
                ) : (
                  <span className="gl-card-seller">{sellerName}</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

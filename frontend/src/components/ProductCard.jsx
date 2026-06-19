import { Link } from 'react-router-dom';
import { formatCurrency } from '../api/client';
import { useStore } from '../context/StoreContext';
import { calcDiscount, calcInstallment } from '../utils/commerce';

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

const CONDITION_LABELS = { new: 'Nova', used: 'Usada', reconditioned: 'Recond.' };
const ORIGIN_LABELS = { original: 'OEM', parallel: 'Paralela', remanufactured: 'Remanuf.' };

export default function ProductCard({ product, shippingHint }) {
  const { config } = useStore();
  const inStock = product.in_stock !== false && product.stock > 0;
  const discount = calcDiscount(product.price, product.compare_at_price);
  const freeShipping = Number(product.price) >= Number(config.free_shipping_min || 299);
  const installment = calcInstallment(product.price);

  return (
    <article className="gl-card">
      <Link to={`/peca/${product.slug}/`} className="gl-card-media">
        {discount && <span className="gl-card-tag">-{discount}%</span>}
        {product.is_featured && <span className="gl-card-tag gl-card-tag--hot">Destaque</span>}
        {product.part_condition && (
          <span className="gl-card-tag gl-card-tag--cond">
            {CONDITION_LABELS[product.part_condition] || product.part_condition}
          </span>
        )}
        {product.warranty_days > 0 && (
          <span className="gl-card-tag gl-card-tag--warranty">{product.warranty_days}d garantia</span>
        )}
        {freeShipping && <span className="gl-card-tag gl-card-tag--ship">Frete grátis</span>}
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} loading="lazy" />
        ) : (
          <span className="gl-card-ph">⚙</span>
        )}
      </Link>

      <div className="gl-card-body">
        {product.brand && <span className="gl-card-brand">{product.brand}</span>}
        {product.part_origin && product.part_origin !== 'original' && (
          <span className="gl-card-origin">{ORIGIN_LABELS[product.part_origin] || product.part_origin}</span>
        )}
        <h3 className="gl-card-title">
          <Link to={`/peca/${product.slug}/`}>{product.name}</Link>
        </h3>

        <div className="gl-card-price-row">
          {product.compare_at_price && (
            <span className="gl-card-old">{formatCurrency(product.compare_at_price)}</span>
          )}
          <span className="gl-card-price">{formatCurrency(product.price)}</span>
        </div>

        <div className="gl-card-promo-strip">
          <span className="gl-card-installment">
            <strong>12x {installment}</strong> sem juros
          </span>
          {!freeShipping && (
            <span className="gl-card-ship-hint">
              Frete grátis acima de {formatCurrency(config.free_shipping_min || 299)}
            </span>
          )}
        </div>

        {shippingHint && (
          <div className="gl-card-cep-hint">{shippingHint}</div>
        )}

        <div className="gl-card-foot">
          {product.seller_name && (
            <Link to={`/loja/${product.seller_slug}/`} className="gl-card-seller">
              Vendido por {product.seller_name}
            </Link>
          )}
          {inStock ? (
            <span className="gl-card-stock">Em estoque</span>
          ) : (
            <span className="gl-card-oos">Indisponível</span>
          )}
        </div>
      </div>
    </article>
  );
}

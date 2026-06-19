import { Link } from 'react-router-dom';
import { useStore } from '../context/StoreContext';

export default function CouponBanner() {
  const { config } = useStore();

  return (
    <div className="coupon-banner wrap">
      <div className="coupon-banner-inner">
        <div className="coupon-banner-text">
          <span className="coupon-banner-code">BEMVINDO10</span>
          <div>
            <strong>10% off na sua primeira compra</strong>
            <span>Pedido mínimo R$ 50 · use no checkout</span>
          </div>
        </div>
        <div className="coupon-banner-actions">
          <span className="coupon-banner-hint">
            Frete grátis acima de R$ {Number(config.free_shipping_min || 299).toFixed(0)}
          </span>
          <Link to="/pecas/" className="btn btn-light btn-sm">Comprar agora</Link>
        </div>
      </div>
    </div>
  );
}

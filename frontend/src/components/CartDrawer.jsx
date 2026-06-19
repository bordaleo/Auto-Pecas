import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatCurrency } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { quoteCartShipping, resolveShippingZip } from '../utils/shipping';

export default function CartDrawer() {
  const { items, total, drawerOpen, setDrawerOpen } = useCart();
  const { user } = useAuth();
  const [shippingLabel, setShippingLabel] = useState('Informe o CEP no carrinho');

  useEffect(() => {
    if (!drawerOpen || !items.length) return;
    const zip = resolveShippingZip(user);
    quoteCartShipping(total, zip)
      .then((q) => setShippingLabel(q.label))
      .catch(() => setShippingLabel('Informe o CEP no carrinho'));
  }, [drawerOpen, items.length, total, user?.shipping_zip]);

  if (!drawerOpen) return null;

  return (
    <>
      <div className="drawer-overlay" onClick={() => setDrawerOpen(false)} aria-hidden />
      <aside className="drawer" role="dialog" aria-label="Carrinho">
        <div className="drawer-header">
          <strong>Seu carrinho</strong>
          <button type="button" className="btn-ghost" onClick={() => setDrawerOpen(false)}>
            Fechar
          </button>
        </div>
        <div className="drawer-body">
          {items.length === 0 ? (
            <p className="empty">Carrinho vazio</p>
          ) : (
            items.map((item) => (
              <div key={item.product_id} className="drawer-item">
                {item.image_url ? (
                  <img src={item.image_url} alt="" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                ) : (
                  <div style={{ width: 56, height: 56, background: '#ededed', borderRadius: 4, display: 'grid', placeItems: 'center' }}>⚙</div>
                )}
                <div style={{ flex: 1 }}>
                  <strong style={{ fontSize: '0.85rem' }}>{item.name}</strong>
                  <div style={{ color: 'rgba(0,0,0,.55)', fontSize: '0.78rem' }}>
                    {item.quantity}x {formatCurrency(item.price)}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="drawer-footer">
          <div className="summary-row">
            <span>Subtotal</span>
            <span>{formatCurrency(total)}</span>
          </div>
          {items.length > 0 && (
            <div className="summary-row">
              <span>Frete estimado</span>
              <span>{shippingLabel}</span>
            </div>
          )}
          <Link to="/carrinho/" className="btn btn-secondary btn-full" style={{ marginTop: '0.75rem' }} onClick={() => setDrawerOpen(false)}>
            Ver carrinho
          </Link>
          <Link to="/checkout/" className="btn btn-primary btn-full" style={{ marginTop: '0.5rem' }} onClick={() => setDrawerOpen(false)}>
            Finalizar compra
          </Link>
        </div>
      </aside>
    </>
  );
}

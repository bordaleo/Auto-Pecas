import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatCurrency } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useStore } from '../context/StoreContext';
import { persistZip, quoteCartShipping, resolveShippingZip } from '../utils/shipping';

export default function Cart() {
  const { items, total, updateQty, removeItem } = useCart();
  const { user } = useAuth();
  const { config } = useStore();
  const [zip, setZip] = useState('');
  const [shippingFee, setShippingFee] = useState(0);
  const [shippingLabel, setShippingLabel] = useState('Informe o CEP');
  const freeMin = Number(config.free_shipping_min || 299);

  useEffect(() => {
    setZip(resolveShippingZip(user));
  }, [user]);

  useEffect(() => {
    if (!items.length) return;
    quoteCartShipping(total, zip)
      .then((q) => {
        setShippingFee(q.fee);
        setShippingLabel(q.label);
      })
      .catch(() => {
        setShippingFee(0);
        setShippingLabel('Informe o CEP');
      });
  }, [items.length, total, zip]);

  const handleZipBlur = () => {
    if (zip.replace(/\D/g, '').length >= 8) persistZip(zip, user);
  };

  if (!items.length) {
    return (
      <div className="wrap internal-page">
        <div className="internal-page-card">
          <p className="state-empty">Carrinho vazio. <Link to="/pecas/">Ver catálogo</Link></p>
        </div>
      </div>
    );
  }

  const grandTotal = total + shippingFee;

  return (
    <div className="wrap internal-page cart-page">
      <header className="internal-page-head">
        <h1>Seu carrinho</h1>
        <p>{items.length} item(ns) · Frete grátis acima de {formatCurrency(freeMin)}</p>
      </header>

      <div className="internal-page-grid">
        <div className="internal-page-card cart-items-card">
          <table className="cart-table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Qtd</th>
                <th>Subtotal</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.product_id}>
                  <td>
                    <div className="cart-item-info">
                      {item.image_url ? (
                        <img src={item.image_url} alt="" className="cart-item-thumb" />
                      ) : (
                        <span className="cart-item-ph">⚙</span>
                      )}
                      <Link to={`/peca/${item.slug}/`}>{item.name}</Link>
                    </div>
                  </td>
                  <td>
                    <div className="qty-row cart-qty">
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => updateQty(item.product_id, item.quantity - 1)}>−</button>
                      <span>{item.quantity}</span>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => updateQty(item.product_id, item.quantity + 1)}>+</button>
                    </div>
                  </td>
                  <td>{formatCurrency(item.price * item.quantity)}</td>
                  <td>
                    <button type="button" className="btn-ghost cart-remove" onClick={() => removeItem(item.product_id)}>
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <aside className="internal-page-card cart-summary-card">
          <h2>Resumo</h2>
          <div className="form-group">
            <label>CEP para calcular frete</label>
            <input
              value={zip}
              onChange={(e) => setZip(e.target.value)}
              onBlur={handleZipBlur}
              placeholder="00000-000"
            />
            {!user?.shipping_zip && (
              <p className="form-hint">
                <Link to="/perfil/">Salve seu CEP no perfil</Link> para pré-preencher no checkout.
              </p>
            )}
          </div>
          <div className="summary-card summary-card--flat">
            <div className="summary-row"><span>Subtotal</span><span>{formatCurrency(total)}</span></div>
            <div className="summary-row"><span>Frete</span><span>{shippingLabel}</span></div>
            <div className="summary-row summary-total"><span>Total estimado</span><span>{formatCurrency(grandTotal)}</span></div>
          </div>
          <p className="coupon-hint">Primeira compra? Use <strong>BEMVINDO10</strong> no checkout.</p>
          <Link to="/checkout/" className="btn btn-accent btn-full">Finalizar compra</Link>
        </aside>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { api, formatCurrency, getToken } from '../api/client';
import PixPaymentPanel from '../components/PixPaymentPanel';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useStore } from '../context/StoreContext';
import { useToast } from '../context/ToastContext';

function loadMercadoPagoScript() {
  return new Promise((resolve, reject) => {
    if (window.MercadoPago) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://sdk.mercadopago.com/js/v2';
    script.onload = resolve;
    script.onerror = reject;
    document.body.appendChild(script);
  });
}

function normalizeZip(zip) {
  return (zip || '').replace(/\D/g, '');
}

export default function Checkout() {
  const { user } = useAuth();
  const { items, total, clearCart } = useCart();
  const { config } = useStore();
  const { showToast } = useToast();
  const { openAuth } = useOutletContext();
  const navigate = useNavigate();
  const brickRef = useRef(null);
  const brickControllerRef = useRef(null);

  const [deliveryMethod, setDeliveryMethod] = useState('delivery');
  const [shippingFee, setShippingFee] = useState(0);
  const [shippingLabel, setShippingLabel] = useState('Informe o CEP');
  const [shippingBreakdown, setShippingBreakdown] = useState([]);
  const [showPayment, setShowPayment] = useState(false);
  const [paymentUrl, setPaymentUrl] = useState('');
  const [preferenceId, setPreferenceId] = useState('');
  const [orderAmount, setOrderAmount] = useState(total);
  const [couponCode, setCouponCode] = useState('BEMVINDO10');
  const [discount, setDiscount] = useState(0);
  const [couponLabel, setCouponLabel] = useState('');
  const [brickError, setBrickError] = useState('');
  const [pixPayment, setPixPayment] = useState(null);
  const [subOrders, setSubOrders] = useState([]);
  const [orderGroupId, setOrderGroupId] = useState(null);
  const [form, setForm] = useState({
    shipping_zip: '',
    shipping_address: '',
    shipping_city: '',
    shipping_state: '',
    customer_name: user?.name || '',
    customer_phone: user?.phone || '',
    order_email: user?.email || '',
    notes: '',
  });

  const freeMin = Number(config.free_shipping_min || 299);

  useEffect(() => {
    if (user) {
      setForm((prev) => ({
        ...prev,
        customer_name: user.name || '',
        customer_phone: user.phone || '',
        order_email: user.email || '',
        shipping_zip: user.shipping_zip || prev.shipping_zip,
        shipping_address: user.shipping_address || prev.shipping_address,
        shipping_city: user.shipping_city || prev.shipping_city,
        shipping_state: user.shipping_state || prev.shipping_state,
      }));
    }
  }, [user]);

  const quoteShipping = async (method = deliveryMethod, zip = form.shipping_zip) => {
    if (method === 'pickup') {
      setShippingFee(0);
      setShippingLabel('Retirada grátis');
      setShippingBreakdown([]);
      return;
    }

    const digits = normalizeZip(zip);
    if (digits.length < 8) {
      if (total >= freeMin) {
        setShippingFee(0);
        setShippingLabel('Frete grátis');
      } else {
        setShippingFee(0);
        setShippingLabel('Informe o CEP');
      }
      setShippingBreakdown([]);
      return;
    }

    try {
      const quote = await api('/shop/shipping/quote/', {
        method: 'POST',
        body: JSON.stringify({
          delivery_method: 'delivery',
          shipping_zip: digits,
          subtotal: Number(total).toFixed(2),
          cart_items: items.map((item) => ({
            product_id: item.product_id,
            price: item.price,
            quantity: item.quantity,
            weight_kg: item.weight_kg || 1,
            width_cm: item.width_cm || 20,
            height_cm: item.height_cm || 10,
            length_cm: item.length_cm || 30,
          })),
        }),
      });
      const fee = parseFloat(quote.shipping_fee) || 0;
      const breakdown = quote.breakdown || [];
      setShippingFee(fee);
      setShippingBreakdown(breakdown);

      if (breakdown.length > 1) {
        const parts = breakdown.map((row) => {
          const rowFee = parseFloat(row.shipping_fee) || 0;
          const label = rowFee === 0 ? 'grátis' : formatCurrency(rowFee);
          return `${row.store_name}: ${label}`;
        });
        setShippingLabel(parts.join(' · '));
      } else {
        const service = quote.shipping_service_name ? ` (${quote.shipping_service_name})` : '';
        const days = quote.shipping_days ? ` · ${quote.shipping_days} dia(s)` : '';
        setShippingLabel(fee === 0 ? 'Frete grátis' : `${formatCurrency(fee)}${service}${days}`);
      }
    } catch (error) {
      setShippingFee(0);
      setShippingLabel('Informe o CEP');
      setShippingBreakdown([]);
      showToast(error.message);
    }
  };

  useEffect(() => {
    quoteShipping();
  }, [deliveryMethod, total, form.shipping_zip, freeMin, items]);

  const applyCoupon = async () => {
    if (!couponCode.trim()) {
      setDiscount(0);
      setCouponLabel('');
      return;
    }
    try {
      const result = await api('/shop/coupon/validate/', {
        method: 'POST',
        body: JSON.stringify({ code: couponCode.trim(), subtotal: Number(total).toFixed(2) }),
      });
      const d = parseFloat(result.discount_amount) || 0;
      setDiscount(d);
      setCouponLabel(`Cupom ${result.code} aplicado`);
      showToast(`Desconto de ${formatCurrency(d)}`);
    } catch (error) {
      setDiscount(0);
      setCouponLabel('');
      showToast(error.message);
    }
  };

  useEffect(() => {
    setOrderAmount(Math.max(0, total + shippingFee - discount));
  }, [total, shippingFee, discount]);

  useEffect(() => {
    if (!pixPayment || !preferenceId) return undefined;

    const poll = async () => {
      try {
        const status = await api(`/payments/status/${preferenceId}`);
        if (status.status === 'approved') {
          clearCart();
          showToast('PIX confirmado! Pedido aprovado.');
          navigate('/conta/pedidos/');
        }
      } catch {
        /* continua polling */
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, [pixPayment, preferenceId, clearCart, navigate, showToast]);

  const handlePaymentResult = (data, resolve, reject) => {
    const hasPix = Boolean(data.pix_qr_code || data.pix_qr_code_base64);

    if (data.status === 'approved') {
      clearCart();
      showToast('Pagamento aprovado!');
      setTimeout(() => navigate('/conta/pedidos/'), 1500);
      resolve();
      return;
    }

    if (['pending', 'in_process'].includes(data.status) && hasPix) {
      setPixPayment({
        qrCode: data.pix_qr_code || '',
        qrCodeBase64: data.pix_qr_code_base64 || '',
      });
      showToast('PIX gerado! Escaneie o QR Code ou copie o código.');
      resolve();
      return;
    }

    if (['pending', 'in_process'].includes(data.status)) {
      showToast('Pagamento pendente — acompanhe em Meus pedidos.');
      resolve();
      return;
    }

    showToast('Pagamento não aprovado');
    reject();
  };

  const initBrick = async (prefId, amount, payerEmail) => {
    const publicKey = config.mercadopago_public_key;
    if (!publicKey) {
      setBrickError('Mercado Pago não configurado.');
      return;
    }

    const brickAmount = Number(Number(amount).toFixed(2));

    try {
      await loadMercadoPagoScript();
      if (brickControllerRef.current?.unmount) {
        brickControllerRef.current.unmount();
        brickControllerRef.current = null;
      }
      if (brickRef.current) brickRef.current.innerHTML = '';

      const mp = new window.MercadoPago(publicKey, {
        locale: 'pt-BR',
        advancedFraudPrevention: false,
      });

      const initialization = {
        amount: brickAmount,
        preferenceId: prefId,
      };
      if (payerEmail) {
        initialization.payer = { email: payerEmail };
      }

      brickControllerRef.current = await mp.bricks().create('payment', 'paymentBrick_container', {
        initialization,
        customization: {
          paymentMethods: {
            creditCard: 'all',
            debitCard: 'all',
            ticket: 'all',
            bankTransfer: 'all',
            mercadoPago: 'all',
            maxInstallments: 12,
          },
        },
        callbacks: {
          onReady: () => setBrickError(''),
          onError: (error) => {
            const msg = error?.message || 'Não foi possível carregar o formulário de pagamento.';
            setBrickError(`${msg} Use o botão "Pagar no Mercado Pago" acima.`);
          },
          onSubmit: ({ formData }) => new Promise((resolve, reject) => {
            api('/payments/process', {
              method: 'POST',
              body: JSON.stringify({ preference_id: prefId, form_data: formData }),
            })
              .then((data) => {
                handlePaymentResult(data, resolve, reject);
              })
              .catch((error) => {
                showToast(error.message);
                reject();
              });
          }),
        },
      });
    } catch (error) {
      setBrickError('Formulário indisponível. Use o botão "Pagar no Mercado Pago" acima.');
    }
  };

  const validateCheckout = () => {
    if (deliveryMethod === 'delivery') {
      const digits = normalizeZip(form.shipping_zip);
      if (digits.length !== 8) {
        showToast('Informe um CEP válido com 8 dígitos.');
        return false;
      }
      if (!form.shipping_address.trim() || !form.shipping_city.trim() || !form.shipping_state.trim()) {
        showToast('Preencha endereço, cidade e UF para entrega.');
        return false;
      }
      if (total < freeMin && shippingFee <= 0 && shippingLabel === 'Informe o CEP') {
        showToast('Calcule o frete informando seu CEP.');
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!validateCheckout()) return;

    try {
      await quoteShipping();
      const order = await api('/shop/checkout/', {
        method: 'POST',
        body: JSON.stringify({
          items: items.map((item) => ({ product_id: item.product_id, quantity: item.quantity })),
          ...form,
          delivery_method: deliveryMethod,
          coupon_code: discount > 0 ? couponCode.trim() : '',
        }),
      });
      const pref = await api('/shop/payment/preference/', {
        method: 'POST',
        body: JSON.stringify({ order_id: order.id }),
      });
      const redirectUrl = pref.init_point || pref.sandbox_init_point || '';
      setPreferenceId(pref.preference_id);
      setPaymentUrl(redirectUrl);
      setOrderAmount(parseFloat(order.total_amount || order.amount));
      setSubOrders(order.sub_orders || []);
      setOrderGroupId(order.order_group_id || null);
      setShowPayment(true);
      setBrickError('');
      setPixPayment(null);
      const payerEmail = form.order_email || user?.email || '';
      const brickAmount = pref.brick_amount ?? parseFloat(order.total_amount || order.amount);
      await initBrick(pref.preference_id, brickAmount, payerEmail);
      showToast('Pedido criado! Escolha como pagar abaixo.');
    } catch (error) {
      showToast(error.message);
    }
  };

  if (!getToken()) {
    return (
      <div className="wrap internal-page checkout-wrap">
        <div className="internal-page-card">
          <p className="state-empty">
            Faça login para finalizar.{' '}
            <button type="button" className="btn btn-accent" onClick={() => openAuth('login')}>Entrar</button>
          </p>
        </div>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="wrap internal-page checkout-wrap">
        <div className="internal-page-card">
          <p className="state-empty">Carrinho vazio. <Link to="/pecas/">Ver catálogo</Link></p>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap internal-page checkout-wrap">
      <header className="internal-page-head">
        <h1>Finalizar compra</h1>
        <p>Pagamento seguro via Mercado Pago · PIX, cartão ou boleto</p>
      </header>
      <div className="checkout-grid internal-page-grid">
      <form className="internal-page-card checkout-page" onSubmit={handleSubmit}>
        <h2 className="checkout-section-title">Como receber</h2>
        <div className="delivery-options">
          <label className={`delivery-option${deliveryMethod === 'delivery' ? ' active' : ''}`}>
            <input
              type="radio"
              name="delivery_method"
              value="delivery"
              checked={deliveryMethod === 'delivery'}
              onChange={() => setDeliveryMethod('delivery')}
            />
            <div>
              <strong>Entrega</strong>
              <div style={{ fontSize: '0.82rem', color: 'rgba(0,0,0,.55)' }}>
                Frete pelo CEP · grátis acima de {formatCurrency(freeMin)}
              </div>
            </div>
          </label>
          <label className={`delivery-option${deliveryMethod === 'pickup' ? ' active' : ''}`}>
            <input
              type="radio"
              name="delivery_method"
              value="pickup"
              checked={deliveryMethod === 'pickup'}
              onChange={() => setDeliveryMethod('pickup')}
            />
            <div>
              <strong>Retirada na loja</strong>
              <div style={{ fontSize: '0.82rem', color: 'rgba(0,0,0,.55)' }}>
                {config.store_address || 'Endereço da loja'} · sem frete
              </div>
            </div>
          </label>
        </div>

        {deliveryMethod === 'delivery' && (
          <>
            <h2 className="checkout-section-title">Endereço de entrega</h2>
            <div className="form-group">
              <label>CEP *</label>
              <input
                value={form.shipping_zip}
                onChange={(e) => setForm({ ...form, shipping_zip: e.target.value })}
                onBlur={() => quoteShipping('delivery', form.shipping_zip)}
                placeholder="00000-000"
              />
            </div>
            <div className="form-group">
              <label>Endereço *</label>
              <input value={form.shipping_address} onChange={(e) => setForm({ ...form, shipping_address: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Cidade *</label>
              <input value={form.shipping_city} onChange={(e) => setForm({ ...form, shipping_city: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>UF *</label>
              <input value={form.shipping_state} onChange={(e) => setForm({ ...form, shipping_state: e.target.value.toUpperCase() })} maxLength={2} required />
            </div>
          </>
        )}

        <h2 className="checkout-section-title">Seus dados</h2>
        <div className="form-group">
          <label>Nome completo</label>
          <input value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} required />
        </div>
        <div className="form-group">
          <label>Telefone</label>
          <input value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input type="email" value={form.order_email} onChange={(e) => setForm({ ...form, order_email: e.target.value })} required />
        </div>
        <div className="form-group">
          <label>Observações</label>
          <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </div>

        <div className="form-group coupon-group">
          <label>Cupom de desconto</label>
          <div className="coupon-row">
            <input
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
              placeholder="BEMVINDO10"
            />
            <button type="button" className="btn btn-secondary btn-sm" onClick={applyCoupon}>Aplicar</button>
          </div>
          {couponLabel && <p className="coupon-applied">{couponLabel}</p>}
          <p className="coupon-hint">Primeira compra? Use <strong>BEMVINDO10</strong> (10% off)</p>
        </div>

        <div className="summary-card">
          <div className="summary-row"><span>Subtotal ({items.length} item(ns))</span><span>{formatCurrency(total)}</span></div>
          <div className="summary-row"><span>Frete</span><span>{shippingLabel}</span></div>
          {shippingBreakdown.length > 1 && (
            <div className="checkout-shipping-breakdown">
              {shippingBreakdown.map((row) => (
                <div key={row.seller_key} className="checkout-shipping-row">
                  <span>
                    {row.store_name}
                    {row.is_official && <span className="store-badge store-badge--sm">Oficial</span>}
                    {row.ships_from_platform && !row.is_official && (
                      <span className="store-badge store-badge--sm store-badge--ship">Envio Sandroni</span>
                    )}
                  </span>
                  <span>
                    {parseFloat(row.shipping_fee) === 0
                      ? 'Grátis'
                      : formatCurrency(row.shipping_fee)}
                  </span>
                </div>
              ))}
            </div>
          )}
          {discount > 0 && (
            <div className="summary-row summary-discount"><span>Desconto</span><span>- {formatCurrency(discount)}</span></div>
          )}
          <div className="summary-row summary-total"><span>Total</span><span>{formatCurrency(orderAmount)}</span></div>
        </div>

        {!showPayment && (
          <button type="submit" className="btn btn-accent btn-full" style={{ marginTop: '1rem' }}>
            Continuar para pagamento
          </button>
        )}
      </form>

      {showPayment && (
        <div className="internal-page-card checkout-page payment-panel">
          <h2 className="checkout-section-title">Pagamento Mercado Pago</h2>
          <p className="form-hint payment-panel-total">
            Total do pedido: <strong>{formatCurrency(orderAmount)}</strong>
            {orderGroupId && ` · Compra #${orderGroupId}`}
          </p>

          {subOrders.length > 1 && (
            <div className="checkout-sub-orders">
              <h3>Entregas por loja</h3>
              {subOrders.map((sub) => (
                <div key={sub.id} className="checkout-sub-order">
                  <strong>{sub.store_label || sub.fulfillment_seller_name}</strong>
                  <span>
                    {formatCurrency(sub.amount)}
                    {sub.shipping_fee > 0 ? ` · Frete ${formatCurrency(sub.shipping_fee)}` : ' · Frete grátis'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {pixPayment ? (
            <PixPaymentPanel
              amount={orderAmount}
              qrCode={pixPayment.qrCode}
              qrCodeBase64={pixPayment.qrCodeBase64}
              onCopy={() => showToast('Código PIX copiado!')}
            />
          ) : (
            <>
              {paymentUrl && (
                <a href={paymentUrl} className="btn btn-accent btn-full payment-redirect-btn">
                  Pagar no Mercado Pago (recomendado)
                </a>
              )}
              <p className="form-hint payment-redirect-hint">
                Abre a página segura do Mercado Pago. Funciona melhor se o formulário abaixo não carregar (ex.: Edge com bloqueio de rastreamento).
              </p>

              {brickError && <p className="payment-brick-error">{brickError}</p>}
              <div id="paymentBrick_container" ref={brickRef} className="payment-brick-host" />
            </>
          )}
        </div>
      )}
      </div>
    </div>
  );
}

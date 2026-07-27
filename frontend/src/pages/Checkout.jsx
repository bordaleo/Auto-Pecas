import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { Truck, MapPin, Store, CreditCard, ExternalLink } from 'lucide-react';
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
  const [checkoutStep, setCheckoutStep] = useState('shipping');
  const [showPayment, setShowPayment] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [payOption, setPayOption] = useState('methods'); // methods | redirect
  const [paymentUrl, setPaymentUrl] = useState('');
  const [preferenceId, setPreferenceId] = useState('');
  const [orderAmount, setOrderAmount] = useState(total);
  const [couponCode, setCouponCode] = useState('');
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
            maxInstallments: 12,
          },
        },
        callbacks: {
          onReady: () => setBrickError(''),
          onError: (error) => {
            const msg = error?.message || 'Não foi possível carregar o formulário de pagamento.';
            setBrickError(`${msg} Selecione "Mercado Pago" acima para abrir a página do Mercado Pago.`);
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
      setBrickError('Formulário indisponível. Selecione a opção Mercado Pago acima.');
    }
  };

  useEffect(() => {
    if (checkoutStep !== 'payment' || payOption !== 'methods' || !preferenceId || pixPayment) return undefined;
    const timer = setTimeout(() => {
      const payerEmail = form.order_email || user?.email || '';
      initBrick(preferenceId, orderAmount, payerEmail);
    }, 50);
    return () => clearTimeout(timer);
  }, [checkoutStep, payOption, preferenceId, pixPayment]);

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

  const goToPaymentStep = async (event) => {
    event?.preventDefault?.();
    if (preferenceId) {
      setCheckoutStep('payment');
      setShowPayment(true);
      return;
    }
    if (!validateCheckout()) return;
    if (submitting) return;

    setSubmitting(true);
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
      setCheckoutStep('payment');
      setPayOption('methods');
      setBrickError('');
      setPixPayment(null);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      showToast(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const itemCount = items.reduce((sum, item) => sum + (item.quantity || 1), 0);

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

      <nav className="checkout-steps" aria-label="Etapas do checkout">
        <button
          type="button"
          className={`checkout-step${checkoutStep === 'shipping' ? ' is-active' : ''}${checkoutStep === 'payment' ? ' is-done' : ''}`}
          onClick={() => setCheckoutStep('shipping')}
        >
          <span className="checkout-step__num">1</span>
          <span className="checkout-step__label">Frete e dados</span>
        </button>
        <span className="checkout-steps__divider" aria-hidden="true" />
        <button
          type="button"
          className={`checkout-step${checkoutStep === 'payment' ? ' is-active' : ''}`}
          onClick={() => goToPaymentStep()}
        >
          <span className="checkout-step__num">2</span>
          <span className="checkout-step__label">Pagamento</span>
        </button>
      </nav>

      {checkoutStep === 'shipping' ? (
        <form className="internal-page-card checkout-page checkout-step-panel" onSubmit={goToPaymentStep}>
          <section className="checkout-block">
            <header className="checkout-block__head">
              <h2 className="checkout-section-title">Como receber</h2>
              <p className="checkout-section-lead">Escolha entrega em casa ou retirada na loja.</p>
            </header>

            <div className="delivery-options">
              <label className={`delivery-option${deliveryMethod === 'delivery' ? ' active' : ''}`}>
                <input
                  type="radio"
                  name="delivery_method"
                  value="delivery"
                  checked={deliveryMethod === 'delivery'}
                  onChange={() => setDeliveryMethod('delivery')}
                  disabled={Boolean(preferenceId)}
                />
                <span className="delivery-option__icon" aria-hidden="true">
                  <Truck size={20} />
                </span>
                <div className="delivery-option__content">
                  <strong>Receber em casa</strong>
                  <span>Frete pelo CEP · grátis acima de {formatCurrency(freeMin)}</span>
                </div>
              </label>
              <label className={`delivery-option${deliveryMethod === 'pickup' ? ' active' : ''}`}>
                <input
                  type="radio"
                  name="delivery_method"
                  value="pickup"
                  checked={deliveryMethod === 'pickup'}
                  onChange={() => setDeliveryMethod('pickup')}
                  disabled={Boolean(preferenceId)}
                />
                <span className="delivery-option__icon" aria-hidden="true">
                  <Store size={20} />
                </span>
                <div className="delivery-option__content">
                  <strong>Retirar na loja</strong>
                  <span>Sem frete · {config.store_address || 'endereço da loja'}</span>
                </div>
              </label>
            </div>

            {deliveryMethod === 'delivery' ? (
              <div className="checkout-address">
                <h3 className="checkout-subsection-title">
                  <MapPin size={16} aria-hidden="true" />
                  Endereço de entrega
                </h3>
                <div className="checkout-address-grid">
                  <div className="form-group checkout-field--cep">
                    <label htmlFor="checkout-zip">CEP *</label>
                    <input
                      id="checkout-zip"
                      value={form.shipping_zip}
                      onChange={(e) => setForm({ ...form, shipping_zip: e.target.value })}
                      onBlur={() => quoteShipping('delivery', form.shipping_zip)}
                      placeholder="00000-000"
                      inputMode="numeric"
                      autoComplete="postal-code"
                      disabled={Boolean(preferenceId)}
                    />
                    <p className={`checkout-shipping-feedback${shippingFee === 0 && shippingLabel !== 'Informe o CEP' ? ' is-free' : ''}`}>
                      {shippingLabel}
                    </p>
                  </div>
                  <div className="form-group checkout-field--city">
                    <label htmlFor="checkout-city">Cidade *</label>
                    <input
                      id="checkout-city"
                      value={form.shipping_city}
                      onChange={(e) => setForm({ ...form, shipping_city: e.target.value })}
                      required
                      autoComplete="address-level2"
                      disabled={Boolean(preferenceId)}
                    />
                  </div>
                  <div className="form-group checkout-field--uf">
                    <label htmlFor="checkout-uf">UF *</label>
                    <input
                      id="checkout-uf"
                      value={form.shipping_state}
                      onChange={(e) => setForm({ ...form, shipping_state: e.target.value.toUpperCase() })}
                      maxLength={2}
                      required
                      autoComplete="address-level1"
                      placeholder="SP"
                      disabled={Boolean(preferenceId)}
                    />
                  </div>
                  <div className="form-group checkout-field--full">
                    <label htmlFor="checkout-address">Endereço *</label>
                    <input
                      id="checkout-address"
                      value={form.shipping_address}
                      onChange={(e) => setForm({ ...form, shipping_address: e.target.value })}
                      required
                      autoComplete="street-address"
                      placeholder="Rua, número e complemento"
                      disabled={Boolean(preferenceId)}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="checkout-pickup-note">
                <Store size={18} aria-hidden="true" />
                <div>
                  <strong>Retirada sem frete</strong>
                  <p>Após o pagamento, avisamos por e-mail quando a peça estiver pronta.</p>
                  {config.store_address && <p className="checkout-pickup-note__addr">{config.store_address}</p>}
                </div>
              </div>
            )}
          </section>

          <section className="checkout-block">
            <header className="checkout-block__head">
              <h2 className="checkout-section-title">Seus dados</h2>
            </header>
            <div className="checkout-customer-grid">
              <div className="form-group checkout-field--full">
                <label htmlFor="checkout-name">Nome completo</label>
                <input
                  id="checkout-name"
                  value={form.customer_name}
                  onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
                  required
                  autoComplete="name"
                  disabled={Boolean(preferenceId)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="checkout-phone">Telefone</label>
                <input
                  id="checkout-phone"
                  value={form.customer_phone}
                  onChange={(e) => setForm({ ...form, customer_phone: e.target.value })}
                  autoComplete="tel"
                  disabled={Boolean(preferenceId)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="checkout-email">Email</label>
                <input
                  id="checkout-email"
                  type="email"
                  value={form.order_email}
                  onChange={(e) => setForm({ ...form, order_email: e.target.value })}
                  required
                  autoComplete="email"
                  disabled={Boolean(preferenceId)}
                />
              </div>
              <div className="form-group checkout-field--full">
                <label htmlFor="checkout-notes">Observações <span className="checkout-optional">(opcional)</span></label>
                <textarea
                  id="checkout-notes"
                  rows={2}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="Referência de entrega, horário preferido…"
                  disabled={Boolean(preferenceId)}
                />
              </div>
            </div>
          </section>

          <section className="checkout-block checkout-block--summary">
            <header className="checkout-block__head">
              <h2 className="checkout-section-title">Cupom e total</h2>
            </header>
            <div className="checkout-coupon">
              <label htmlFor="checkout-coupon">Cupom de desconto</label>
              <div className="coupon-row">
                <input
                  id="checkout-coupon"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                  placeholder="BEMVINDO10"
                  autoComplete="off"
                  disabled={Boolean(preferenceId)}
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={applyCoupon}
                  disabled={Boolean(preferenceId)}
                >
                  Aplicar
                </button>
              </div>
              {couponLabel && <p className="coupon-applied">{couponLabel}</p>}
              <p className="coupon-hint">Primeira compra? Use <strong>BEMVINDO10</strong> (10% off)</p>
            </div>

            <div className="summary-card checkout-summary">
              <div className="summary-row">
                <span>Subtotal ({itemCount} item{itemCount === 1 ? '' : 's'})</span>
                <span>{formatCurrency(total)}</span>
              </div>
              <div className="summary-row">
                <span>Frete</span>
                <span>{shippingLabel}</span>
              </div>
              {discount > 0 && (
                <div className="summary-row summary-discount">
                  <span>Desconto</span>
                  <span>- {formatCurrency(discount)}</span>
                </div>
              )}
              <div className="summary-row summary-total">
                <span>Total</span>
                <span>{formatCurrency(orderAmount)}</span>
              </div>
            </div>
          </section>

          <button type="submit" className="btn btn-accent btn-full checkout-continue-btn" disabled={submitting}>
            {submitting ? 'Criando pedido...' : 'Continuar para pagamento'}
          </button>
        </form>
      ) : (
        <div className="checkout-payment-layout">
          <aside className="internal-page-card checkout-page checkout-summary-panel">
            <h2 className="checkout-section-title">Resumo do pedido</h2>
            {couponLabel && <p className="coupon-applied">{couponLabel}</p>}
            <div className="summary-card checkout-summary">
              <div className="summary-row">
                <span>Subtotal ({itemCount} item{itemCount === 1 ? '' : 's'})</span>
                <span>{formatCurrency(total)}</span>
              </div>
              <div className="summary-row">
                <span>Frete</span>
                <span>{shippingLabel}</span>
              </div>
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
                <div className="summary-row summary-discount">
                  <span>Desconto</span>
                  <span>- {formatCurrency(discount)}</span>
                </div>
              )}
              <div className="summary-row summary-total">
                <span>Total</span>
                <span>{formatCurrency(orderAmount)}</span>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-full"
              onClick={() => setCheckoutStep('shipping')}
            >
              Voltar para frete e dados
            </button>
          </aside>

          <div className="internal-page-card checkout-page payment-panel">
            <h2 className="checkout-section-title">Pagamento</h2>
            <p className="payment-panel-total">
              Total do pedido: <strong>{formatCurrency(orderAmount)}</strong>
              {orderGroupId && <span className="payment-panel-order"> · Compra #{orderGroupId}</span>}
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
                <div className="payment-options" role="radiogroup" aria-label="Forma de pagamento">
                  <label className={`payment-option${payOption === 'methods' ? ' is-active' : ''}`}>
                    <input
                      type="radio"
                      name="pay_option"
                      value="methods"
                      checked={payOption === 'methods'}
                      onChange={() => setPayOption('methods')}
                    />
                    <span className="payment-option__icon" aria-hidden="true">
                      <CreditCard size={18} />
                    </span>
                    <span className="payment-option__body">
                      <strong>Cartão, PIX ou boleto</strong>
                      <span>Pague nesta página com segurança</span>
                    </span>
                  </label>
                  {paymentUrl && (
                    <label className={`payment-option${payOption === 'redirect' ? ' is-active' : ''}`}>
                      <input
                        type="radio"
                        name="pay_option"
                        value="redirect"
                        checked={payOption === 'redirect'}
                        onChange={() => setPayOption('redirect')}
                      />
                      <span className="payment-option__icon" aria-hidden="true">
                        <ExternalLink size={18} />
                      </span>
                      <span className="payment-option__body">
                        <strong>Mercado Pago</strong>
                        <span>Abrir a página do Mercado Pago</span>
                      </span>
                    </label>
                  )}
                </div>

                {payOption === 'redirect' && paymentUrl ? (
                  <div className="payment-redirect-box">
                    <p className="payment-redirect-hint">
                      Você será direcionado ao site do Mercado Pago para concluir o pagamento.
                    </p>
                    <a href={paymentUrl} className="btn btn-accent btn-full payment-redirect-btn">
                      Continuar no Mercado Pago
                    </a>
                  </div>
                ) : (
                  <>
                    {brickError && <p className="payment-brick-error">{brickError}</p>}
                    <div id="paymentBrick_container" ref={brickRef} className="payment-brick-host" />
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

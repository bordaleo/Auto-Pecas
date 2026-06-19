import { getSavedZip, saveZip } from '../components/ProductCard';
import { api, formatCurrency, getToken } from '../api/client';

export function resolveShippingZip(user) {
  const fromProfile = user?.shipping_zip?.replace(/\D/g, '');
  if (fromProfile && fromProfile.length >= 8) return user.shipping_zip;
  return getSavedZip();
}

export async function quoteCartShipping(subtotal, zip, deliveryMethod = 'delivery') {
  const digits = (zip || '').replace(/\D/g, '');
  if (deliveryMethod === 'pickup') {
    return { fee: 0, label: 'Retirada grátis', isFree: true };
  }
  if (digits.length < 8) {
    return { fee: 0, label: 'Informe o CEP', isFree: false, needsZip: true };
  }
  const quote = await api('/shop/shipping/quote/', {
    method: 'POST',
    body: JSON.stringify({
      delivery_method: 'delivery',
      shipping_zip: digits,
      subtotal,
    }),
  });
  const fee = parseFloat(quote.shipping_fee) || 0;
  return {
    fee,
    label: fee === 0 ? 'Frete grátis' : formatCurrency(fee),
    isFree: quote.is_free,
    needsZip: false,
  };
}

export function persistZip(zip, user) {
  saveZip(zip);
  if (getToken() && user?.email && zip.replace(/\D/g, '').length >= 8) {
    api('/auth/profile', {
      method: 'PUT',
      body: JSON.stringify({ shipping_zip: zip }),
    }).catch(() => {});
  }
}

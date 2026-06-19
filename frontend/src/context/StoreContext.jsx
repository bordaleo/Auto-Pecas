import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';

const StoreContext = createContext(null);

const DEFAULT_CONFIG = {
  store_name: 'Galelugi Peças',
  store_tagline: 'Frete grátis em milhares de peças',
  store_address: '',
  free_shipping_min: 299,
  store_whatsapp: '',
  mercadopago_public_key: '',
  marketplace_commission_percent: 12,
  google_analytics_id: '',
  meta_pixel_id: '',
};

export function StoreProvider({ children }) {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [whatsappUrl, setWhatsappUrl] = useState('https://wa.me/5511999999999');
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    api('/system-config')
      .then(setConfig)
      .catch(() => setConfig(DEFAULT_CONFIG));

    api('/categories/')
      .then((data) => setCategories(data.results || data))
      .catch(() => setCategories([]));

    api('/contact/whatsapp/')
      .then((data) => {
        if (data?.url) setWhatsappUrl(data.url);
      })
      .catch(() => {});
  }, []);

  const value = useMemo(
    () => ({ config, whatsappUrl, categories }),
    [config, whatsappUrl, categories],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used within StoreProvider');
  return ctx;
}

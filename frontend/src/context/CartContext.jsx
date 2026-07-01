import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, getToken } from '../api/client';
import { useAuth } from './AuthContext';
import { trackSearchPurchase } from '../utils/catalogAnalytics';

const CART_KEY = 'galelugi_cart';
const CartContext = createContext(null);

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY) || '[]');
  } catch {
    return [];
  }
}

function productId(value) {
  return Number(value);
}

export function CartProvider({ children }) {
  const [items, setItems] = useState(readCart);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
  }, [items]);

  useEffect(() => {
    if (!getToken() || !user?.email || items.length === 0) return;
    const timer = setTimeout(() => {
      api('/shop/cart/sync/', {
        method: 'POST',
        body: JSON.stringify({
          email: user.email,
          items: items.map((item) => ({
            product_id: item.product_id,
            name: item.name,
            price: item.price,
            quantity: item.quantity,
            image_url: item.image_url,
          })),
        }),
      }).catch(() => {});
    }, 2000);
    return () => clearTimeout(timer);
  }, [items, user?.email]);

  const addItem = useCallback((product, qty = 1) => {
    const pid = productId(product.id);
    if (!product || pid <= 0) return false;

    setItems((prev) => {
      const next = [...prev];
      const index = next.findIndex((item) => productId(item.product_id) === pid);
      const entry = {
        product_id: pid,
        name: product.name,
        slug: product.slug,
        price: parseFloat(product.price) || 0,
        image_url: product.image_url || '',
        sku: product.sku || '',
        quantity: qty,
        stock: Number(product.stock) || 0,
        weight_kg: product.weight_kg || 1,
        width_cm: product.width_cm || 20,
        height_cm: product.height_cm || 10,
        length_cm: product.length_cm || 30,
        seller_id: product.seller_id || null,
        seller_name: product.seller_name || '',
        seller_slug: product.seller_slug || '',
        seller_is_official: Boolean(product.seller_is_official),
        seller_ships_from_platform: Boolean(product.seller_ships_from_platform),
      };
      if (index >= 0) next[index] = { ...next[index], quantity: next[index].quantity + qty };
      else next.push(entry);
      return next;
    });
    trackSearchPurchase(pid);
    setDrawerOpen(true);
    return true;
  }, []);

  const updateQty = useCallback((id, qty) => {
    setItems((prev) =>
      prev.map((item) =>
        item.product_id === id ? { ...item, quantity: Math.max(1, qty) } : item,
      ),
    );
  }, []);

  const removeItem = useCallback((id) => {
    setItems((prev) => prev.filter((item) => item.product_id !== id));
  }, []);

  const clearCart = useCallback(() => setItems([]), []);

  const total = useMemo(
    () => items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [items],
  );

  const count = useMemo(
    () => items.reduce((sum, item) => sum + item.quantity, 0),
    [items],
  );

  const value = useMemo(
    () => ({
      items,
      total,
      count,
      drawerOpen,
      setDrawerOpen,
      addItem,
      updateQty,
      removeItem,
      clearCart,
    }),
    [items, total, count, drawerOpen, addItem, updateQty, removeItem, clearCart],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within CartProvider');
  return ctx;
}

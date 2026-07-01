import { api } from '../api/client';

const ATTRIBUTION_KEY = 'catalog_search_attribution';

export function setSearchAttribution(term, source = 'typed') {
  const clean = (term || '').trim();
  if (!clean) return;
  try {
    sessionStorage.setItem(ATTRIBUTION_KEY, JSON.stringify({
      term: clean,
      source,
      at: Date.now(),
    }));
  } catch {
    /* ignore */
  }
}

export function getSearchAttribution() {
  try {
    const raw = sessionStorage.getItem(ATTRIBUTION_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data?.term) return null;
    if (Date.now() - (data.at || 0) > 24 * 60 * 60 * 1000) {
      sessionStorage.removeItem(ATTRIBUTION_KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

export function clearSearchAttribution() {
  try {
    sessionStorage.removeItem(ATTRIBUTION_KEY);
  } catch {
    /* ignore */
  }
}

export function trackCatalogEvent(payload) {
  api('/catalog/search-events/', {
    method: 'POST',
    body: JSON.stringify(payload),
  }).catch(() => {});
}

export function trackSearch(term, filters, resultCount, source = 'typed') {
  const clean = (term || '').trim();
  if (!clean) return;
  setSearchAttribution(clean, source);
  trackCatalogEvent({
    event_type: 'search',
    term: clean,
    source,
    result_count: resultCount,
    filters: filters || {},
  });
}

export function trackPopularClick(term, filters) {
  const clean = (term || '').trim();
  if (!clean) return;
  setSearchAttribution(clean, 'popular');
  trackCatalogEvent({
    event_type: 'popular_click',
    term: clean,
    source: 'popular',
    filters: filters || {},
  });
}

export function trackSearchPurchase(productId) {
  const attr = getSearchAttribution();
  if (!attr?.term || !productId) return;
  trackCatalogEvent({
    event_type: 'purchase',
    term: attr.term,
    source: attr.source || 'typed',
    product_id: productId,
  });
}

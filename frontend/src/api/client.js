const API = '/api/v1';

export function formatCurrency(value) {
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function formatCnpj(value) {
  const digits = String(value || '').replace(/\D/g, '').slice(0, 14);
  if (digits.length <= 2) return digits;
  if (digits.length <= 5) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  if (digits.length <= 8) return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5)}`;
  if (digits.length <= 12) {
    return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8)}`;
  }
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

export function getToken() {
  return localStorage.getItem('access_token') || '';
}

export function setToken(token) {
  if (token) localStorage.setItem('access_token', token);
  else localStorage.removeItem('access_token');
}

function parseError(data) {
  if (!data) return 'Erro na requisição';
  if (typeof data.detail === 'string') return data.detail;
  if (typeof data === 'object') {
    return Object.entries(data)
      .map(([key, value]) => {
        const text = Array.isArray(value) ? value.join(', ') : String(value);
        if (key === 'password_confirm') return 'Confirme sua senha (campos devem ser iguais).';
        if (key === 'email' && text.includes('já está cadastrado')) {
          return 'Este email já tem conta. Use Entrar ou cadastre outro email.';
        }
        return text;
      })
      .join(' ');
  }
  return 'Erro na requisição';
}

export async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API}${path}`, {
    credentials: options.credentials || 'same-origin',
    ...options,
    headers,
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    if (response.status === 429) {
      throw new Error(
        typeof data?.detail === 'string'
          ? data.detail
          : 'Muitas tentativas. Aguarde alguns minutos e tente novamente.',
      );
    }
    throw new Error(parseError(data));
  }
  return data;
}

/** API do painel operacional (sessão Django via cookie). */
export async function painelApi(path, options = {}) {
  return api(path, { credentials: 'include', ...options });
}

export function buildWhatsAppProductUrl(baseUrl, product) {
  const text = encodeURIComponent(
    `Olá! Tenho dúvida sobre compatibilidade da peça "${product.name}"`
    + (product.oem_code ? ` (OEM ${product.oem_code})` : '')
    + (product.sku ? ` / SKU ${product.sku}` : '')
    + '. Podem me ajudar?',
  );
  return `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}text=${text}`;
}

export function productList(data) {
  if (Array.isArray(data)) return data;
  return data?.results || [];
}

export function productCount(data, list) {
  return data?.count ?? list.length;
}

/** Busca todas as páginas de produtos (até maxPages). */
export async function fetchProductPages(basePath, { maxPages = 4, pageSize = 60 } = {}) {
  const buildUrl = (page) => {
    const sep = basePath.includes('?') ? '&' : '?';
    return `${basePath}${sep}page=${page}&page_size=${pageSize}`;
  };

  let page = 1;
  let all = [];
  let total = 0;

  while (page <= maxPages) {
    const data = await api(buildUrl(page));
    const list = productList(data);
    total = productCount(data, list);
    all = all.concat(list);
    if (all.length >= total || list.length < pageSize) break;
    page += 1;
  }

  return { results: all, count: total };
}

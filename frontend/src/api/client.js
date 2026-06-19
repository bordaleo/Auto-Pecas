const API = '/api/v1';

export function formatCurrency(value) {
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
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

  if (!response.ok) throw new Error(parseError(data));
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

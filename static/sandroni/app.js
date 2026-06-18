/* AutoPeças Sandroni */
const Sandroni = (() => {
  const API = '/api/v1';
  const CART_KEY = 'sandroni_cart';
  const fmt = n => Number(n).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  let storeConfig = { store_address: 'Rua São Sabino, 262', free_shipping_min: 299 };

  const getToken = () => localStorage.getItem('access_token') || '';
  const setToken = t => { t ? localStorage.setItem('access_token', t) : localStorage.removeItem('access_token'); updateAuthUI(); };

  async function api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${API}${path}`, { ...opts, headers });
    let data = null;
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) {
      let msg = data?.detail;
      if (!msg && data && typeof data === 'object') {
        msg = Object.entries(data).map(([k, v]) => {
          const text = Array.isArray(v) ? v.join(', ') : String(v);
          if (k === 'password_confirm') return 'Confirme sua senha (campos devem ser iguais).';
          if (k === 'email' && text.includes('já está cadastrado')) {
            return 'Este email já tem conta. Use Entrar ou cadastre outro email.';
          }
          return text;
        }).join(' ');
      }
      if (!msg) msg = 'Erro na requisição';
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }

  function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

  function toast(msg) {
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    document.getElementById('toast-container')?.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  /* ── Cart ── */
  const getCart = () => { try { return JSON.parse(localStorage.getItem(CART_KEY) || '[]'); } catch { return []; } };
  const saveCart = c => { localStorage.setItem(CART_KEY, JSON.stringify(c)); updateCartUI(); };

  function productId(value) { return Number(value); }

  function openCartDrawer() {
    const drawer = document.getElementById('cart-drawer');
    if (drawer) {
      drawer.hidden = false;
      updateCartUI();
    }
  }

  function addToCart(product, qty = 1) {
    if (!product || productId(product.id) <= 0) {
      toast('Não foi possível adicionar ao carrinho.');
      return;
    }
    const cart = getCart();
    const pid = productId(product.id);
    const i = cart.findIndex(x => productId(x.product_id) === pid);
    const item = {
      product_id: pid,
      name: product.name,
      slug: product.slug,
      price: parseFloat(product.price) || 0,
      image_url: product.image_url || '',
      sku: product.sku || '',
      quantity: qty,
      stock: Number(product.stock) || 0,
    };
    if (i >= 0) cart[i].quantity += qty;
    else cart.push(item);
    saveCart(cart);
    toast(`${product.name} adicionado ao carrinho`);
    openCartDrawer();
  }

  function updateCartQty(id, qty) {
    saveCart(getCart().map(i => i.product_id === id ? { ...i, quantity: Math.max(1, qty) } : i));
  }

  function removeFromCart(id) { saveCart(getCart().filter(i => i.product_id !== id)); }
  function cartTotal() { return getCart().reduce((s, i) => s + i.price * i.quantity, 0); }

  function updateCartUI() {
    const cart = getCart();
    const count = cart.reduce((s, i) => s + i.quantity, 0);
    const badge = document.getElementById('cart-count');
    if (badge) badge.textContent = count;
    const drawer = document.getElementById('cart-drawer-items');
    const totalEl = document.getElementById('cart-drawer-total');
    if (drawer) {
      drawer.innerHTML = cart.length ? cart.map(i => `
        <div class="drawer-item">
          ${i.image_url ? `<img src="${i.image_url}" alt="">` : '<div style="width:56px;height:56px;background:#f0f2f5;border-radius:4px;display:grid;place-items:center;font-size:1.2rem">⚙</div>'}
          <div style="flex:1"><strong style="font-size:.85rem">${esc(i.name)}</strong>
          <div style="color:#5c6b7a;font-size:.78rem">${i.quantity}x ${fmt(i.price)}</div></div>
        </div>`).join('') : '<p class="empty">Carrinho vazio</p>';
    }
    if (totalEl) totalEl.textContent = fmt(cartTotal());
  }

  function productCard(p) {
    const stock = p.in_stock !== false && p.stock > 0;
    const featured = p.is_featured;
    const img = p.image_url
      ? `<img src="${p.image_url}" alt="${esc(p.name)}" loading="lazy">`
      : '<span class="ph">⚙</span>';
    return `<article class="product-card${featured ? ' product-card--featured' : ''}">
      <a href="/peca/${p.slug}/" class="product-img">
        ${featured ? '<span class="product-badge">Destaque</span>' : ''}
        ${img}
      </a>
      <div class="product-body">
        <h3><a href="/peca/${p.slug}/">${esc(p.name)}</a></h3>
        <div class="product-meta">${esc(p.brand)}${p.sku ? ' · ' + esc(p.sku) : ''}</div>
        <div class="product-foot">
          <div><span class="price">${fmt(p.price)}</span>${p.compare_at_price ? `<span class="price-old">${fmt(p.compare_at_price)}</span>` : ''}</div>
          <span class="${stock ? 'stock-ok' : 'stock-no'}">${stock ? 'Em estoque' : 'Esgotado'}</span>
        </div>
        <button type="button" class="btn btn-primary btn-sm btn-full" style="margin-top:.65rem" data-add="${p.id}" ${stock ? '' : 'disabled'}>Adicionar</button>
      </div>
    </article>`;
  }

  function bindAddButtons(el, products) {
    const byId = new Map((products || []).map(p => [productId(p.id), p]));
    el?.querySelectorAll('[data-add]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();
        const p = byId.get(productId(btn.dataset.add));
        if (p) addToCart(p);
        else toast('Não foi possível adicionar ao carrinho.');
      });
    });
  }

  /* ── Categories nav ── */
  async function loadCategoriesNav() {
    try {
      const cats = await api('/categories/');
      const list = cats.results || cats;
      const nav = document.getElementById('cat-nav-list');
      const mobile = document.getElementById('mobile-cats');
      if (nav) {
        nav.innerHTML = list.map(c =>
          `<a href="/pecas/?category=${c.slug}">${c.icon ? c.icon + ' ' : ''}${esc(c.name)}</a>`
        ).join('');
      }
      if (mobile) {
        mobile.innerHTML = `<h4>Categorias</h4>` + list.map(c =>
          `<a href="/pecas/?category=${c.slug}">${esc(c.name)}</a>`
        ).join('');
      }
      return list;
    } catch { return []; }
  }

  async function loadStoreConfig() {
    try {
      storeConfig = await api('/system-config');
    } catch (_) {}
  }

  async function initWhatsApp() {
    let url = 'https://wa.me/5511974452478?text=' + encodeURIComponent('Olá! Gostaria de informações sobre peças automotivas.');
    try {
      const data = await api('/contact/whatsapp/');
      if (data?.url) url = data.url;
    } catch (_) {}
    document.querySelectorAll('#whatsapp-fab, #footer-whatsapp, #heritage-whatsapp, #cta-whatsapp').forEach(el => {
      if (el) el.href = url;
    });
    const fab = document.getElementById('whatsapp-fab');
    if (fab) fab.hidden = false;
  }

  async function quoteShipping(deliveryMethod, zip) {
    const quote = await api('/shop/shipping/quote/', {
      method: 'POST',
      body: JSON.stringify({
        delivery_method: deliveryMethod,
        shipping_zip: zip || '',
        subtotal: cartTotal(),
      }),
    });
    return quote;
  }

  /* ── Auth ── */
  function openAuth(tab = 'login') {
    document.getElementById('auth-modal').hidden = false;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    document.getElementById('login-form').hidden = tab !== 'login';
    document.getElementById('register-form').hidden = tab !== 'register';
    document.getElementById('verify-form').hidden = tab !== 'verify';
  }

  async function updateAuthUI() {
    const btn = document.getElementById('btn-auth');
    if (!getToken()) {
      if (btn) { btn.querySelector('span').textContent = 'Entrar'; btn.onclick = () => openAuth('login'); }
      return;
    }
    try {
      const me = await api('/auth/me');
      const name = me.name?.split(' ')[0] || 'Conta';
      if (btn) { btn.querySelector('span').textContent = name; btn.onclick = () => { window.location.href = '/perfil/'; }; }
      if (me.is_staff) {
        const m = document.getElementById('mobile-manage');
        if (m) m.hidden = false;
      }
    } catch { setToken(''); }
  }

  function initAuth() {
    document.querySelectorAll('[data-close-modal]').forEach(el =>
      el.addEventListener('click', () => { document.getElementById('auth-modal').hidden = true; }));
    document.querySelectorAll('.tab').forEach(t =>
      t.addEventListener('click', () => openAuth(t.dataset.tab)));
    document.getElementById('footer-login')?.addEventListener('click', e => { e.preventDefault(); openAuth('login'); });
    document.getElementById('btn-forgot')?.addEventListener('click', async () => {
      const email = document.querySelector('#login-form [name=email]')?.value;
      if (!email) return toast('Informe seu email');
      try { await api('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }); toast('Código enviado!'); }
      catch (e) { toast(e.message); }
    });
    document.getElementById('login-form')?.addEventListener('submit', async e => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        const d = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: fd.get('email'), password: fd.get('password') }) });
        setToken(d.access_token);
        document.getElementById('auth-modal').hidden = true;
        toast('Bem-vindo à AutoPeças Sandroni!');
      } catch (err) { showMsg(err.message, true); }
    });
    document.getElementById('register-form')?.addEventListener('submit', async e => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const password = fd.get('password');
      const confirm = fd.get('password_confirm');
      if (password !== confirm) {
        showMsg('As senhas não coincidem.', true);
        return;
      }
      try {
        const d = await api('/auth/register', { method: 'POST', body: JSON.stringify({
          name: fd.get('name'),
          email: fd.get('email'),
          password,
          password_confirm: confirm,
        })});
        if (d.access_token) {
          setToken(d.access_token);
          document.getElementById('auth-modal').hidden = true;
          toast('Conta criada! Bem-vindo à AutoPeças Sandroni.');
          return;
        }
        localStorage.setItem('pending_verify_email', fd.get('email'));
        openAuth('verify');
        showMsg('Código enviado para seu email.');
      } catch (err) {
        showMsg(err.message, true);
        if (err.message.includes('já tem conta') || err.message.includes('já está cadastrado')) {
          const email = fd.get('email');
          const loginEmail = document.querySelector('#login-form [name=email]');
          if (loginEmail && email) loginEmail.value = email;
          setTimeout(() => openAuth('login'), 1200);
        }
      }
    });
    document.getElementById('verify-form')?.addEventListener('submit', async e => {
      e.preventDefault();
      try {
        const d = await api('/auth/verify-email', { method: 'POST', body: JSON.stringify({
          email: localStorage.getItem('pending_verify_email'),
          code: new FormData(e.target).get('code'),
        })});
        if (d.access_token) setToken(d.access_token);
        document.getElementById('auth-modal').hidden = true;
        toast('Conta verificada!');
      } catch (err) { showMsg(err.message, true); }
    });
  }

  function showMsg(msg, err) {
    const el = document.getElementById('auth-message');
    if (el) { el.textContent = msg; el.className = 'form-msg' + (err ? ' error' : ' ok'); }
  }

  function initUI() {
    document.getElementById('btn-open-cart')?.addEventListener('click', () => {
      document.getElementById('cart-drawer').hidden = false;
      updateCartUI();
    });
    document.querySelectorAll('[data-close-drawer]').forEach(el =>
      el.addEventListener('click', () => { document.getElementById('cart-drawer').hidden = true; }));
    document.getElementById('mobile-toggle')?.addEventListener('click', () => {
      document.getElementById('mobile-menu').hidden = false;
    });
    document.querySelectorAll('[data-close-mobile]').forEach(el =>
      el.addEventListener('click', () => { document.getElementById('mobile-menu').hidden = true; }));
    const params = new URLSearchParams(window.location.search);
    if (params.get('q')) {
      const inp = document.getElementById('header-search');
      if (inp) inp.value = params.get('q');
    }
  }

  /* ── Car brands marquee ── */
  const CAR_BRANDS = [
    { name: 'Volkswagen', abbr: 'VW', query: 'VW', color: '#001E50' },
    { name: 'Chevrolet', abbr: 'GM', query: 'Chevrolet', color: '#FFC72C' },
    { name: 'Fiat', abbr: 'FI', query: 'Fiat', color: '#9D2235' },
    { name: 'Ford', abbr: 'FD', query: 'Ford', color: '#003478' },
    { name: 'Toyota', abbr: 'TY', query: 'Toyota', color: '#EB0A1E' },
    { name: 'Honda', abbr: 'HN', query: 'Honda', color: '#CC0000' },
    { name: 'Hyundai', abbr: 'HY', query: 'Hyundai', color: '#002C5F' },
    { name: 'Renault', abbr: 'RN', query: 'Renault', color: '#FFCC33' },
    { name: 'Nissan', abbr: 'NS', query: 'Nissan', color: '#C3002F' },
    { name: 'Jeep', abbr: 'JP', query: 'Jeep', color: '#1B3D2F' },
    { name: 'Peugeot', abbr: 'PG', query: 'Peugeot', color: '#1B4073' },
    { name: 'Citroën', abbr: 'CT', query: 'Citroën', color: '#DA291C' },
    { name: 'Mitsubishi', abbr: 'MT', query: 'Mitsubishi', color: '#E60012' },
    { name: 'Kia', abbr: 'KI', query: 'Kia', color: '#05141F' },
    { name: 'BMW', abbr: 'BM', query: 'BMW', color: '#0066B1' },
    { name: 'Mercedes-Benz', abbr: 'MB', query: 'Mercedes', color: '#1A1A1A' },
  ];

  function brandMarqueeItem(b) {
    return `<a href="/pecas/?q=${encodeURIComponent(b.query)}" class="brand-marquee-item" style="--brand-color:${b.color}" title="Peças para ${esc(b.name)}">
      <span class="brand-marquee-logo">${esc(b.abbr)}</span>${esc(b.name)}
    </a>`;
  }

  const CAT_ACCENTS = {
    motor: '#fff4ec', freios: '#fee2e2', suspensao: '#e0f2fe',
    filtros: '#f0fdf4', eletrica: '#fef9c3', carroceria: '#f3e8ff',
  };

  function initBrandMarquee() {
    const track = document.getElementById('brand-marquee-track');
    const trackRev = document.getElementById('brand-marquee-track-rev');
    const items = CAR_BRANDS.map(brandMarqueeItem).join('');
    if (track) track.innerHTML = items + items;
    if (trackRev) {
      const rev = [...CAR_BRANDS].reverse().map(brandMarqueeItem).join('');
      trackRev.innerHTML = rev + rev;
    }
  }

  /* ── Promo carousel ── */
  function initPromoCarousel() {
    const carousel = document.getElementById('promo-carousel');
    const track = document.getElementById('promo-track');
    const dotsEl = document.getElementById('promo-dots');
    const progressEl = document.getElementById('promo-progress')?.querySelector('span');
    if (!carousel || !track) return;

    const slides = track.querySelectorAll('.promo-slide');
    const total = slides.length;
    const AUTOPLAY_MS = 5500;
    let current = 0;
    let autoplayTimer = null;
    let progressTimer = null;
    let progressStart = 0;
    let touchStartX = 0;

    function setProgress(pct) {
      if (progressEl) progressEl.style.width = `${pct}%`;
    }

    function runProgress() {
      if (progressTimer) cancelAnimationFrame(progressTimer);
      progressStart = performance.now();
      const tick = now => {
        const pct = Math.min(((now - progressStart) / AUTOPLAY_MS) * 100, 100);
        setProgress(pct);
        if (pct < 100) progressTimer = requestAnimationFrame(tick);
      };
      progressTimer = requestAnimationFrame(tick);
    }

    function goTo(index) {
      current = ((index % total) + total) % total;
      track.style.transform = `translateX(-${current * 100}%)`;
      dotsEl?.querySelectorAll('.promo-dot').forEach((d, i) => d.classList.toggle('active', i === current));
      runProgress();
    }

    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }

    function startAutoplay() {
      stopAutoplay();
      runProgress();
      autoplayTimer = setInterval(next, AUTOPLAY_MS);
    }
    function stopAutoplay() {
      if (autoplayTimer) clearInterval(autoplayTimer);
      if (progressTimer) cancelAnimationFrame(progressTimer);
    }

    if (dotsEl) {
      dotsEl.innerHTML = Array.from({ length: total }, (_, i) =>
        `<button type="button" class="promo-dot${i === 0 ? ' active' : ''}" role="tab" aria-label="Slide ${i + 1}" data-index="${i}"></button>`
      ).join('');
      dotsEl.querySelectorAll('.promo-dot').forEach(dot =>
        dot.addEventListener('click', () => { goTo(Number(dot.dataset.index)); startAutoplay(); }));
    }

    document.getElementById('promo-prev')?.addEventListener('click', () => { prev(); startAutoplay(); });
    document.getElementById('promo-next')?.addEventListener('click', () => { next(); startAutoplay(); });

    carousel.addEventListener('mouseenter', stopAutoplay);
    carousel.addEventListener('mouseleave', startAutoplay);

    carousel.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, { passive: true });
    carousel.addEventListener('touchend', e => {
      const diff = touchStartX - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 50) { diff > 0 ? next() : prev(); startAutoplay(); }
    }, { passive: true });

    startAutoplay();
  }

  /* ── Pages ── */
  async function loadHome() {
    initBrandMarquee();
    initPromoCarousel();
    try {
      const [cats, featured, all] = await Promise.all([
        api('/categories/'), api('/products/?featured=1'), api('/products/'),
      ]);
      const catList = cats.results || cats;
      const feat = featured.results || featured;
      const catEl = document.getElementById('home-categories');
      if (catEl) {
        catEl.innerHTML = catList.map(c => `
          <a href="/pecas/?category=${c.slug}" class="cat-card" style="--cat-accent:${CAT_ACCENTS[c.slug] || 'var(--orange-soft)'}">
            <div class="cat-card-icon">${c.icon || '🔧'}</div>
            <strong>${esc(c.name)}</strong>
          </a>`).join('');
      }
      const quickEl = document.getElementById('quick-cats');
      if (quickEl && catList.length) {
        quickEl.innerHTML = catList.map(c =>
          `<a href="/pecas/?category=${c.slug}" class="quick-cat"><span class="quick-cat-icon">${c.icon || '🔧'}</span>${esc(c.name)}</a>`
        ).join('');
      }
      const featEl = document.getElementById('home-featured');
      if (featEl) {
        featEl.innerHTML = feat.length ? feat.slice(0, 8).map(productCard).join('') : '<p class="empty">Cadastre peças em <a href="/gerenciar/">Gerenciar</a></p>';
        bindAddButtons(featEl, feat.slice(0, 8));
      }
      const stat = document.getElementById('stat-products');
      if (stat) stat.textContent = all.count ?? (all.results || all).length ?? 0;
    } catch (e) { console.error(e); }
  }

  async function loadCatalog() {
    const params = new URLSearchParams(window.location.search);
    document.getElementById('filter-q').value = params.get('q') || '';
    renderCatalogFilters(params);
    try {
      const [cats, brands] = await Promise.all([api('/categories/'), api('/products/brands/')]);
      const catEl = document.getElementById('filter-category');
      catEl.innerHTML = '<option value="">Todas</option>' + (cats.results || cats).map(c =>
        `<option value="${c.slug}" ${params.get('category') === c.slug ? 'selected' : ''}>${esc(c.name)}</option>`).join('');
      document.getElementById('filter-brand').innerHTML = '<option value="">Todas</option>' + brands.map(b =>
        `<option value="${b}" ${params.get('brand') === b ? 'selected' : ''}>${esc(b)}</option>`).join('');
    } catch (_) {}
    document.getElementById('btn-apply-filters')?.addEventListener('click', () => {
      const p = new URLSearchParams();
      const q = document.getElementById('filter-q').value;
      const cat = document.getElementById('filter-category').value;
      const brand = document.getElementById('filter-brand').value;
      if (q) p.set('q', q);
      if (cat) p.set('category', cat);
      if (brand) p.set('brand', brand);
      if (document.getElementById('filter-stock').checked) p.set('in_stock', '1');
      window.location.href = '/pecas/?' + p.toString();
    });
    await fetchCatalog(params);
  }

  function renderCatalogFilters(params) {
    const el = document.getElementById('catalog-active-filters');
    if (!el) return;
    const chips = [];
    const q = params.get('q');
    const brand = params.get('brand');
    const cat = params.get('category');
    if (q) {
      const carBrand = CAR_BRANDS.find(b => b.query.toLowerCase() === q.toLowerCase() || b.name.toLowerCase() === q.toLowerCase());
      chips.push(`<span class="filter-chip">${carBrand ? `Veículo: ${esc(carBrand.name)}` : `Busca: ${esc(q)}`} <a href="/pecas/" title="Remover">×</a></span>`);
    }
    if (brand) chips.push(`<span class="filter-chip">Marca: ${esc(brand)}</span>`);
    if (cat) chips.push(`<span class="filter-chip">Categoria: ${esc(cat)}</span>`);
    if (params.get('featured')) chips.push(`<span class="filter-chip">Em destaque</span>`);
    if (chips.length) { el.innerHTML = chips.join(''); el.hidden = false; }
    else el.hidden = true;
  }

  async function fetchCatalog(params) {
    try {
      const data = await api('/products/' + (params.toString() ? '?' + params : ''));
      let products = data.results || data;
      const sort = document.getElementById('sort-select')?.value;
      if (sort === 'price_asc') products = [...products].sort((a, b) => a.price - b.price);
      if (sort === 'price_desc') products = [...products].sort((a, b) => b.price - a.price);
      document.getElementById('catalog-count').textContent = `${data.count ?? products.length} peça(s) encontrada(s)`;
      const el = document.getElementById('catalog-products');
      el.innerHTML = products.length ? products.map(productCard).join('') : '<p class="empty">Nenhuma peça encontrada. <a href="/pecas/">Ver todas</a></p>';
      bindAddButtons(el, products);
      document.getElementById('sort-select')?.addEventListener('change', () => fetchCatalog(params));
    } catch (e) {
      document.getElementById('catalog-products').innerHTML = `<p class="empty">${esc(e.message)}</p>`;
    }
  }

  async function loadProduct(slug) {
    const el = document.getElementById('product-detail');
    try {
      const p = await api(`/products/${slug}/`);
      const images = [p.image_url, ...(p.images || []).map(i => i.url)].filter(Boolean);
      el.innerHTML = `<div class="product-layout">
        <div>
          <div class="gallery-main" id="gallery-main">${images[0] ? `<img src="${images[0]}" alt="${esc(p.name)}" id="main-img">` : '<span class="ph" style="font-size:4rem;opacity:.2">⚙</span>'}</div>
          ${images.length > 1 ? `<div class="gallery-thumbs">${images.map((u,i) => `<img src="${u}" class="${i===0?'active':''}" data-thumb="${u}">`).join('')}</div>` : ''}
        </div>
        <div class="product-info">
          <div class="tags">
            ${p.category ? `<span class="tag">${esc(p.category.name)}</span>` : ''}
            ${p.brand ? `<span class="tag">${esc(p.brand)}</span>` : ''}
            ${p.sku ? `<span class="tag">SKU ${esc(p.sku)}</span>` : ''}
            ${p.oem_code ? `<span class="tag">OEM ${esc(p.oem_code)}</span>` : ''}
          </div>
          <h1>${esc(p.name)}</h1>
          <div class="product-price">${fmt(p.price)}</div>
          <span class="${p.in_stock ? 'stock-ok' : 'stock-no'}">${p.in_stock ? `${p.stock} un. em estoque` : 'Indisponível'}</span>
          <p class="product-desc">${esc(p.description) || 'Peça automotiva AutoPeças Sandroni.'}</p>
          ${p.compatible_vehicles ? `<div class="compat-box"><strong>Compatível:</strong> ${esc(p.compatible_vehicles)}</div>` : ''}
          <div class="qty-row">
            <div class="qty">
              <button type="button" id="qty-min">−</button>
              <input id="qty-val" value="1" readonly>
              <button type="button" id="qty-plus">+</button>
            </div>
            <button type="button" class="btn btn-primary" id="btn-add" ${p.in_stock ? '' : 'disabled'}>Adicionar ao carrinho</button>
          </div>
        </div>
      </div>`;
      document.querySelectorAll('[data-thumb]').forEach(t => t.addEventListener('click', () => {
        document.getElementById('main-img').src = t.dataset.thumb;
        document.querySelectorAll('[data-thumb]').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
      }));
      let qty = 1;
      document.getElementById('qty-min').onclick = () => { qty = Math.max(1, --qty); document.getElementById('qty-val').value = qty; };
      document.getElementById('qty-plus').onclick = () => { qty = Math.min(p.stock || 99, ++qty); document.getElementById('qty-val').value = qty; };
      document.getElementById('btn-add').onclick = () => addToCart(p, qty);
    } catch { el.innerHTML = '<p class="empty">Peça não encontrada. <a href="/pecas/">Ver catálogo</a></p>'; }
  }

  function renderCartPage() {
    const el = document.getElementById('cart-page');
    const cart = getCart();
    if (!cart.length) { el.innerHTML = '<p class="empty">Carrinho vazio. <a href="/pecas/">Ver catálogo</a></p>'; return; }
    el.innerHTML = cart.map(i => `
      <div class="cart-row">
        ${i.image_url ? `<img src="${i.image_url}" alt="">` : '<div style="width:72px;height:72px;background:#f0f2f5;border-radius:8px;display:grid;place-items:center">⚙</div>'}
        <div>
          <strong><a href="/peca/${i.slug}/">${esc(i.name)}</a></strong>
          <div style="color:#5c6b7a;font-size:.85rem;margin:.25rem 0">${fmt(i.price)} cada</div>
          <div class="qty"><button data-min="${i.product_id}">−</button><input value="${i.quantity}" readonly><button data-plus="${i.product_id}">+</button></div>
        </div>
        <div style="text-align:right">
          <strong>${fmt(i.price * i.quantity)}</strong>
          <button class="btn-link" data-rm="${i.product_id}" style="display:block;margin-top:.35rem;color:#dc2626">Remover</button>
        </div>
      </div>`).join('') + `
      <div class="cart-summary">
        <div class="cart-summary-row"><span>Total</span><strong>${fmt(cartTotal())}</strong></div>
        <a href="/checkout/" class="btn btn-primary btn-full">Finalizar compra</a>
      </div>`;
    el.querySelectorAll('[data-min]').forEach(b => b.onclick = () => { const i = cart.find(x => x.product_id === +b.dataset.min); if (i) updateCartQty(i.product_id, i.quantity - 1); renderCartPage(); });
    el.querySelectorAll('[data-plus]').forEach(b => b.onclick = () => { const i = cart.find(x => x.product_id === +b.dataset.plus); if (i) updateCartQty(i.product_id, i.quantity + 1); renderCartPage(); });
    el.querySelectorAll('[data-rm]').forEach(b => b.onclick = () => { removeFromCart(+b.dataset.rm); renderCartPage(); });
  }

  async function initCheckout() {
    await loadStoreConfig();
    const el = document.getElementById('checkout-page');
    if (!getToken()) {
      el.innerHTML = '<div class="panel empty">Faça login para finalizar. <button class="btn btn-primary" id="ck-login">Entrar</button></div>';
      document.getElementById('ck-login').onclick = () => openAuth('login');
      return;
    }
    if (!getCart().length) { el.innerHTML = '<p class="empty">Carrinho vazio. <a href="/pecas/">Ver catálogo</a></p>'; return; }
    let me = {};
    try { me = await api('/auth/me'); } catch (_) {}
    const pickupAddr = storeConfig.store_address || 'Rua São Sabino, 262';
    const freeMin = Number(storeConfig.free_shipping_min || 299);
    el.innerHTML = `<div class="checkout-grid">
      <form class="form panel" id="checkout-form">
        <h2 class="checkout-title">Como receber</h2>
        <div class="delivery-options">
          <label class="delivery-option">
            <input type="radio" name="delivery_method" value="delivery" checked>
            <span><strong>Entrega</strong><small>Frete calculado pelo CEP · grátis acima de ${fmt(freeMin)}</small></span>
          </label>
          <label class="delivery-option">
            <input type="radio" name="delivery_method" value="pickup">
            <span><strong>Retirada na loja</strong><small>${esc(pickupAddr)} · sem frete</small></span>
          </label>
        </div>
        <div id="delivery-fields">
          <h2 class="checkout-title">Endereço de entrega</h2>
          <label><span>CEP *</span><input name="shipping_zip" id="shipping-zip" inputmode="numeric" placeholder="00000-000"></label>
          <label><span>Endereço *</span><input name="shipping_address"></label>
          <label><span>Cidade *</span><input name="shipping_city"></label>
          <label><span>UF *</span><input name="shipping_state" maxlength="2" placeholder="SP"></label>
        </div>
        <h2 class="checkout-title">Seus dados</h2>
        <label><span>Nome completo</span><input name="customer_name" required value="${esc(me.name||'')}"></label>
        <label><span>Telefone</span><input name="customer_phone" value="${esc(me.phone||'')}"></label>
        <label><span>Email</span><input name="order_email" type="email" value="${esc(me.email||'')}"></label>
        <label><span>Observações</span><textarea name="notes" rows="2"></textarea></label>
        <div class="cart-summary-box">
          <div class="cart-summary-row"><span>Subtotal (${getCart().length} item(ns))</span><strong id="ck-subtotal">${fmt(cartTotal())}</strong></div>
          <div class="cart-summary-row"><span>Frete</span><strong id="ck-shipping">Calcule o CEP</strong></div>
          <div class="cart-summary-row total"><span>Total</span><strong id="ck-total">${fmt(cartTotal())}</strong></div>
        </div>
        <button type="submit" class="btn btn-primary btn-full">Continuar para pagamento</button>
      </form>
      <div class="panel payment-box" id="payment-box" hidden>
        <h2 class="checkout-title">Pagamento</h2>
        <div id="paymentBrick_container"></div>
      </div>
    </div>`;

    let shippingFee = 0;
    let orderTotal = cartTotal();

    async function refreshShipping() {
      const method = document.querySelector('[name=delivery_method]:checked')?.value || 'delivery';
      const zip = document.getElementById('shipping-zip')?.value || '';
      const deliveryFields = document.getElementById('delivery-fields');
      deliveryFields.hidden = method === 'pickup';
      try {
        const quote = await quoteShipping(method, zip);
        shippingFee = parseFloat(quote.shipping_fee) || 0;
        orderTotal = cartTotal() + shippingFee;
        document.getElementById('ck-shipping').textContent = shippingFee === 0
          ? (method === 'pickup' ? 'Retirada grátis' : 'Frete grátis')
          : fmt(shippingFee);
        document.getElementById('ck-total').textContent = fmt(orderTotal);
      } catch (err) {
        document.getElementById('ck-shipping').textContent = method === 'pickup' ? 'Retirada grátis' : 'Informe o CEP';
        orderTotal = cartTotal();
        document.getElementById('ck-total').textContent = fmt(orderTotal);
        if (method === 'delivery' && zip.replace(/\D/g, '').length >= 8) toast(err.message);
      }
    }

    document.querySelectorAll('[name=delivery_method]').forEach(r =>
      r.addEventListener('change', refreshShipping));
    document.getElementById('shipping-zip')?.addEventListener('blur', refreshShipping);
    refreshShipping();

    document.getElementById('checkout-form').onsubmit = async e => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const method = fd.get('delivery_method') || 'delivery';
      try {
        await refreshShipping();
        const order = await api('/shop/checkout/', { method: 'POST', body: JSON.stringify({
          items: getCart().map(i => ({ product_id: i.product_id, quantity: i.quantity })),
          customer_name: fd.get('customer_name'),
          customer_phone: fd.get('customer_phone'),
          order_email: fd.get('order_email'),
          delivery_method: method,
          shipping_zip: fd.get('shipping_zip'),
          shipping_address: fd.get('shipping_address'),
          shipping_city: fd.get('shipping_city'),
          shipping_state: fd.get('shipping_state'),
          notes: fd.get('notes'),
        })});
        const pref = await api('/shop/payment/preference/', { method: 'POST', body: JSON.stringify({ order_id: order.id }) });
        document.getElementById('payment-box').hidden = false;
        initBrick(pref.preference_id, parseFloat(order.amount));
        toast('Pedido criado! Complete o pagamento.');
      } catch (err) { toast(err.message); }
    };
  }

  function initBrick(preferenceId, amount) {
    if (!window.MercadoPago || !window.MP_PUBLIC_KEY) return toast('Mercado Pago não configurado');
    new MercadoPago(window.MP_PUBLIC_KEY, { locale: 'pt-BR' }).bricks().create('payment', 'paymentBrick_container', {
      initialization: { amount: amount || cartTotal(), preferenceId },
      customization: { paymentMethods: { maxInstallments: 12 } },
      callbacks: {
        onSubmit: ({ formData }) => new Promise((resolve, reject) => {
          api('/payments/process', { method: 'POST', body: JSON.stringify({ preference_id: preferenceId, form_data: formData }) })
            .then(d => {
              if (d.status === 'approved') { localStorage.removeItem(CART_KEY); updateCartUI(); toast('Pagamento aprovado!'); setTimeout(() => location.href = '/pedidos/', 1500); resolve(); }
              else if (['pending','in_process'].includes(d.status)) { toast('Pagamento pendente'); resolve(); }
              else { toast('Pagamento não aprovado'); reject(); }
            }).catch(e => { toast(e.message); reject(); });
        }),
      },
    });
  }

  async function loadOrders() {
    const el = document.getElementById('orders-page');
    if (!getToken()) {
      el.innerHTML = '<div class="panel empty"><button class="btn btn-primary" id="ord-login">Entrar</button></div>';
      document.getElementById('ord-login').onclick = () => openAuth('login');
      return;
    }
    try {
      const orders = await api('/shop/orders/');
      el.innerHTML = orders.length ? orders.map(o => `
        <div class="order-card">
          <div class="order-head"><strong>Pedido #${o.id}</strong><span class="status ${o.status}">${esc(o.status_display)}</span></div>
          <div style="color:#5c6b7a;font-size:.85rem;margin-bottom:.5rem">${new Date(o.created_at).toLocaleString('pt-BR')} · ${fmt(o.amount)}</div>
          <div style="font-size:.82rem;color:#5c6b7a;margin-bottom:.5rem">${esc(o.delivery_method_display || 'Entrega')}${o.shipping_fee > 0 ? ` · Frete ${fmt(o.shipping_fee)}` : ''}</div>
          ${(o.items||[]).map(i => `<div style="font-size:.88rem;padding:.2rem 0">${i.quantity}x ${esc(i.product_name)} — ${fmt(i.subtotal)}</div>`).join('')}
        </div>`).join('') : '<p class="empty">Nenhum pedido. <a href="/pecas/">Comprar peças</a></p>';
    } catch (e) { el.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  async function loadProfile() {
    const el = document.getElementById('profile-page');
    if (!getToken()) { el.innerHTML = '<p class="empty"><button class="btn btn-primary" id="pf-login">Entrar</button></p>'; document.getElementById('pf-login').onclick = () => openAuth('login'); return; }
    try {
      const me = await api('/auth/me');
      el.innerHTML = `<form class="form" id="profile-form">
        <label><span>Nome</span><input name="name" value="${esc(me.name)}"></label>
        <label><span>Email</span><input value="${esc(me.email)}" disabled></label>
        <label><span>Telefone</span><input name="phone" value="${esc(me.phone||'')}"></label>
        <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.5rem">
          <button type="submit" class="btn btn-primary">Salvar</button>
          <button type="button" class="btn btn-outline" id="btn-logout">Sair</button>
          ${me.is_staff ? '<a href="/gerenciar/" class="btn btn-primary">Gerenciar peças</a>' : ''}
        </div>
      </form>`;
      document.getElementById('profile-form').onsubmit = async e => {
        e.preventDefault();
        const fd = new FormData(e.target);
        try { await api('/auth/profile', { method: 'PUT', body: JSON.stringify({ name: fd.get('name'), phone: fd.get('phone') }) }); toast('Salvo!'); }
        catch (err) { toast(err.message); }
      };
      document.getElementById('btn-logout').onclick = async () => { try { await api('/auth/logout', { method: 'POST' }); } catch(_){} setToken(''); location.href = '/'; };
    } catch (e) { el.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  async function initManage() {
    const el = document.getElementById('manage-page');
    if (!getToken()) { el.innerHTML = '<p class="empty"><button class="btn btn-primary" id="mg-login">Entrar como admin</button></p>'; document.getElementById('mg-login').onclick = () => openAuth('login'); return; }
    try {
      const me = await api('/auth/me');
      if (!me.is_staff) { el.innerHTML = '<p class="empty">Acesso restrito a administradores.</p>'; return; }
      const [cats, products] = await Promise.all([api('/categories/'), api('/manage/products/')]);
      const catList = cats.results || cats;
      el.innerHTML = `<div class="manage-grid">
        <form class="form panel" id="product-form">
          <h2 style="font-family:var(--font-display);text-transform:uppercase;margin-bottom:1rem">Nova peça</h2>
          <label><span>Nome *</span><input name="name" required></label>
          <label><span>Descrição</span><textarea name="description" rows="2"></textarea></label>
          <label><span>SKU / Código</span><input name="sku"></label>
          <label><span>Código OEM</span><input name="oem_code"></label>
          <label><span>Marca</span><input name="brand"></label>
          <label><span>Veículos compatíveis</span><textarea name="compatible_vehicles" rows="2"></textarea></label>
          <label><span>Preço (R$) *</span><input name="price" type="number" step="0.01" required></label>
          <label><span>Estoque *</span><input name="stock" type="number" min="0" value="1" required></label>
          <label><span>Categoria</span><select name="category"><option value="">—</option>${catList.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label>
          <label><span>URL da imagem</span><input name="image_url"></label>
          <label><span>Upload foto</span><input type="file" id="image-file" accept="image/*"></label>
          <label class="field-check"><input type="checkbox" name="is_featured"> Destaque</label>
          <label class="field-check"><input type="checkbox" name="is_active" checked> Ativo</label>
          <button type="submit" class="btn btn-primary btn-full">Cadastrar</button>
        </form>
        <div><h2 style="font-family:var(--font-display);text-transform:uppercase;margin-bottom:1rem">Peças (${products.length})</h2>
        <div>${products.map(p=>`<div class="manage-item"><div><strong>${esc(p.name)}</strong><div style="color:#5c6b7a;font-size:.82rem">${fmt(p.price)} · Est: ${p.stock}</div></div><a href="/peca/${p.slug}/" class="btn btn-outline btn-sm">Ver</a></div>`).join('')||'<p class="empty">Nenhuma peça</p>'}</div></div>
      </div>`;
      document.getElementById('image-file').onchange = e => {
        const f = e.target.files[0]; if (!f) return;
        const r = new FileReader();
        r.onload = async () => { try { const res = await api('/manage/upload-image/', { method: 'POST', body: JSON.stringify({ image: r.result }) }); document.querySelector('[name=image_url]').value = res.url; toast('Foto enviada!'); } catch(err){ toast(err.message); } };
        r.readAsDataURL(f);
      };
      document.getElementById('product-form').onsubmit = async e => {
        e.preventDefault();
        const fd = new FormData(e.target);
        try {
          await api('/manage/products/', { method: 'POST', body: JSON.stringify({
            name: fd.get('name'), description: fd.get('description'), sku: fd.get('sku'),
            oem_code: fd.get('oem_code'), brand: fd.get('brand'), compatible_vehicles: fd.get('compatible_vehicles'),
            price: fd.get('price'), stock: fd.get('stock'), image_url: fd.get('image_url'),
            category: fd.get('category') || null, is_featured: fd.get('is_featured') === 'on', is_active: fd.get('is_active') === 'on',
          })});
          toast('Peça cadastrada!'); initManage();
        } catch (err) { toast(err.message); }
      };
    } catch (e) { el.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }

  function handleAuthUrlParams() {
    if (window.location.pathname.includes('verify-email')) openAuth('verify');
  }

  document.addEventListener('DOMContentLoaded', async () => {
    initAuth(); initUI(); updateCartUI(); updateAuthUI();
    await loadStoreConfig();
    initWhatsApp();
    loadCategoriesNav();
  });

  return { loadHome, loadCatalog, loadProduct, renderCartPage, initCheckout, loadOrders, loadProfile, initManage, handleAuthUrlParams, openAuth };
})();

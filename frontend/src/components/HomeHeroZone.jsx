import { useState } from 'react';
import { Check, Copy, Search } from 'lucide-react';
import { useStore } from '../context/StoreContext';

const WELCOME_COUPON = 'BEMVINDO10';

const QUICK_TAGS = [
  'Pastilha de freio',
  'Filtro de ar',
  'Amortecedor',
  'Correia dentada',
  'Vela de ignição',
  'Óleo motor',
];

export default function HomeHeroZone({ onSearch }) {
  const { config } = useStore();
  const [query, setQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const freeShipping = Number(config.free_shipping_min || 299).toFixed(0);

  const submit = (value) => {
    const trimmed = value.trim();
    if (trimmed) onSearch(trimmed);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    submit(query);
  };

  const handleTagClick = (tag) => {
    setQuery(tag);
    submit(tag);
  };

  const handleCopyCoupon = async () => {
    try {
      await navigator.clipboard.writeText(WELCOME_COUPON);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* fallback silencioso */
    }
  };

  return (
    <section className="home-hero-zone wrap" aria-label="Busca e promoções">
      <div className="home-hero-zone__card">
        <div className="home-hero-zone__promo">
          <div className="home-hero-zone__code-wrap">
            <span className="home-hero-zone__code">{WELCOME_COUPON}</span>
            <button
              type="button"
              className="home-hero-zone__copy"
              onClick={handleCopyCoupon}
              aria-label={copied ? 'Código copiado' : `Copiar cupom ${WELCOME_COUPON}`}
            >
              {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
              {copied ? 'Copiado!' : 'Copiar'}
            </button>
          </div>
          <p className="home-hero-zone__promo-text">
            <strong>10% off na primeira compra</strong>
            <span>Pedido mínimo R$ 50 · use no checkout</span>
          </p>
          <span className="home-hero-zone__ship">
            Frete grátis acima de <em>R$ {freeShipping}</em>
          </span>
        </div>

        <div className="home-hero-zone__body">
          <form className="home-hero-zone__search" onSubmit={handleSubmit}>
            <input
              type="search"
              className="home-hero-zone__input"
              placeholder="Peça, OEM, SKU, marca ou veículo..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Buscar peças"
            />
            <button type="submit" className="home-hero-zone__btn">
              <Search size={16} aria-hidden="true" />
              Buscar
            </button>
          </form>

          <div className="home-hero-zone__tags">
            <span className="home-hero-zone__tags-label">Buscas rápidas:</span>
            {QUICK_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                className="home-hero-zone__tag"
                onClick={() => handleTagClick(tag)}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

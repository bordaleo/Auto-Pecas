import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const SLIDES = [
  {
    tone: 'yellow',
    eyebrow: 'Frete grátis',
    title: 'Sua primeira compra',
    highlight: 'com envio grátis',
    desc: 'Milhares de peças automotivas com entrega rápida em todo o Brasil.',
    cta: 'Aproveitar oferta',
    href: '/pecas/?featured=1',
    visual: '🔩',
  },
  {
    tone: 'blue',
    eyebrow: 'Mercado Pago',
    title: 'Pague com segurança',
    highlight: 'PIX · Cartão · Boleto',
    desc: 'Proteção em todas as compras. Parcele em até 12x sem complicação.',
    cta: 'Ver catálogo',
    href: '/pecas/',
    visual: '💳',
  },
  {
    tone: 'green',
    eyebrow: 'Galelugi Peças',
    title: 'Peças originais',
    highlight: 'e paralelas',
    desc: 'Estoque real, as melhores marcas e atendimento especializado.',
    cta: 'Comprar agora',
    href: '/pecas/',
    visual: '🚗',
  },
  {
    tone: 'purple',
    eyebrow: 'Ofertas do dia',
    title: 'Até 60% OFF',
    highlight: 'em destaque',
    desc: 'Motor, freios, filtros, elétrica e muito mais com preço especial.',
    cta: 'Ver ofertas',
    href: '/pecas/?featured=1',
    visual: '⚡',
  },
];

export default function PromoCarousel() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setCurrent((prev) => (prev + 1) % SLIDES.length), 6000);
    return () => clearInterval(timer);
  }, []);

  const prev = () => setCurrent((c) => (c - 1 + SLIDES.length) % SLIDES.length);
  const next = () => setCurrent((c) => (c + 1) % SLIDES.length);

  return (
    <section className="hero wrap" aria-label="Ofertas em destaque">
      <div className="hero-shell">
        <button type="button" className="hero-nav hero-nav--prev" onClick={prev} aria-label="Anterior">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>

        <div className="hero-viewport">
          <div className="hero-track" style={{ transform: `translateX(-${current * 100}%)` }}>
            {SLIDES.map((slide) => (
              <article key={slide.title} className={`hero-slide hero-slide--${slide.tone}`}>
                <div className="hero-slide-content">
                  <span className="hero-eyebrow">{slide.eyebrow}</span>
                  <h2 className="hero-title">
                    {slide.title}
                    <em>{slide.highlight}</em>
                  </h2>
                  <p className="hero-desc">{slide.desc}</p>
                  <Link to={slide.href} className="hero-cta">{slide.cta}</Link>
                </div>
                <div className="hero-slide-visual" aria-hidden="true">
                  <span className="hero-visual-icon">{slide.visual}</span>
                </div>
              </article>
            ))}
          </div>
        </div>

        <button type="button" className="hero-nav hero-nav--next" onClick={next} aria-label="Próximo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      <div className="hero-dots">
        {SLIDES.map((slide, index) => (
          <button
            key={slide.title}
            type="button"
            className={`hero-dot${index === current ? ' is-active' : ''}`}
            aria-label={`Slide ${index + 1}`}
            onClick={() => setCurrent(index)}
          />
        ))}
      </div>
    </section>
  );
}

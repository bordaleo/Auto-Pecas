import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const SLIDES = [
  {
    eyebrow: 'Catálogo Galelugi',
    title: 'A peça certa',
    highlight: 'para o seu veículo',
    desc: 'Originais e paralelas com busca por OEM, marca e compatibilidade.',
    cta: 'Explorar catálogo',
    href: '/pecas/',
  },
  {
    eyebrow: 'Estoque verificado',
    title: 'Compre com',
    highlight: 'confiança total',
    desc: 'Quantidade real, fotos reais e descrição técnica de cada item.',
    cta: 'Ver destaques',
    href: '/pecas/?featured=1',
  },
  {
    eyebrow: 'Pagamento seguro',
    title: 'PIX, cartão',
    highlight: 'ou boleto',
    desc: 'Checkout protegido via Mercado Pago. Parcele em até 12x.',
    cta: 'Começar a comprar',
    href: '/pecas/',
  },
];

export default function HeroBanner() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setCurrent((c) => (c + 1) % SLIDES.length), 7000);
    return () => clearInterval(timer);
  }, []);

  const slide = SLIDES[current];

  return (
    <section className="hero wrap" aria-label="Destaques Galelugi">
      <div className="hero-panel">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-content">
          <span className="eyebrow">{slide.eyebrow}</span>
          <h1 className="hero-title">
            {slide.title}{' '}
            <em>{slide.highlight}</em>
          </h1>
          <p className="hero-desc">{slide.desc}</p>
          <div className="hero-actions">
            <Link to={slide.href} className="btn btn-accent">{slide.cta}</Link>
            <Link to="/pecas/?featured=1" className="btn btn-ghost-light">Ver ofertas</Link>
          </div>
          <div className="hero-dots">
            {SLIDES.map((s, i) => (
              <button
                key={s.title}
                type="button"
                className={`hero-dot${i === current ? ' is-active' : ''}`}
                aria-label={`Slide ${i + 1}`}
                onClick={() => setCurrent(i)}
              />
            ))}
          </div>
        </div>
        <div className="hero-stats" aria-hidden="true">
          <div className="hero-stat">
            <strong>OEM</strong>
            <span>Busca por código</span>
          </div>
          <div className="hero-stat">
            <strong>12x</strong>
            <span>Sem juros</span>
          </div>
          <div className="hero-stat">
            <strong>BR</strong>
            <span>Entrega nacional</span>
          </div>
        </div>
      </div>
    </section>
  );
}

import { Link } from 'react-router-dom';
import { ArrowRight, Tag } from 'lucide-react';

const STAT_CARDS = [
  { value: 'OEM', desc: 'Busca por código original', label: 'Compatibilidade garantida' },
  { value: '12×', desc: 'Sem juros no cartão', label: 'Todas as bandeiras' },
  { value: 'BR', desc: 'Entrega nacional', label: 'Frete rastreado' },
];

export default function HeroSection() {
  return (
    <section className="gl-hero">
      <div className="gl-hero__content">
        <span className="gl-hero__eyebrow">Catálogo Galelugi</span>

        <h1 className="gl-hero__title">
          A peça certa <em>para o seu veículo</em>
        </h1>

        <p className="gl-hero__subtitle">
          Originais e paralelas com busca por código OEM, marca e compatibilidade.
          Encontre em segundos, receba em todo o Brasil.
        </p>

        <div className="gl-hero__ctas">
          <Link to="/pecas/" className="gl-btn gl-btn--primary">
            Explorar catálogo
            <ArrowRight size={16} />
          </Link>
          <Link to="/pecas/?featured=1" className="gl-btn gl-btn--ghost">
            <Tag size={16} />
            Ver ofertas
          </Link>
        </div>
      </div>

      <div className="gl-hero__stats">
        {STAT_CARDS.map((card) => (
          <div key={card.value} className="gl-stat-card">
            <div className="gl-stat-card__value">{card.value}</div>
            <div className="gl-stat-card__desc">{card.desc}</div>
            <div className="gl-stat-card__label">{card.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

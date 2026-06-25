const STATS = [
  { prefix: '+', highlight: '45k', suffix: '', label: 'Peças em catálogo' },
  { prefix: '', highlight: '98', suffix: '%', label: 'Entregas no prazo' },
  { prefix: '+', highlight: '12k', suffix: '', label: 'Clientes atendidos' },
  { prefix: '', highlight: '4.9', suffix: '★', label: 'Avaliação média' },
];

const REVIEWS = [
  {
    stars: 5,
    text: 'Encontrei a pastilha de freio pelo código OEM em menos de 1 minuto. Chegou em 2 dias em São Paulo. Impressionante.',
    author: 'Rodrigo M.',
    vehicle: 'Golf GTI 2019',
  },
  {
    stars: 5,
    text: 'O atendimento via WhatsApp me ajudou a confirmar a compatibilidade antes de comprar. Nunca mais errei de peça.',
    author: 'Ana Paula S.',
    vehicle: 'Corolla 2021',
  },
  {
    stars: 5,
    text: 'Melhor preço que encontrei para o kit de correia. Parcelei em 12x sem juros e chegou muito bem embalado.',
    author: 'Carlos B.',
    vehicle: 'HB20 2020',
  },
];

export default function TrustSection() {
  return (
    <section className="gl-trust">
      <div className="gl-trust__stats">
        {STATS.map((stat) => (
          <div key={stat.label} className="gl-trust__stat-cell">
            <div className="gl-trust__stat-value">
              {stat.prefix}
              <span className="gl-orange-text">{stat.highlight}</span>
              {stat.suffix}
            </div>
            <div className="gl-trust__stat-label">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="gl-trust__reviews">
        {REVIEWS.map((review) => (
          <article key={review.author} className="gl-review-card">
            <div className="gl-review-card__stars" aria-label={`${review.stars} estrelas`}>
              {'★'.repeat(review.stars)}
            </div>
            <p className="gl-review-card__text">&ldquo;{review.text}&rdquo;</p>
            <div className="gl-review-card__author">
              {review.author} · {review.vehicle}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

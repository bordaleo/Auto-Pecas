import { Link } from 'react-router-dom';

const PILLARS = [
  {
    icon: '🔍',
    title: 'Busca inteligente',
    desc: 'Encontre por nome, código OEM, SKU, marca ou veículo compatível.',
  },
  {
    icon: '📦',
    title: 'Estoque real',
    desc: 'Só vendemos o que temos. Sem surpresas na hora da entrega.',
  },
  {
    icon: '🛠️',
    title: 'Especialistas',
    desc: 'Equipe que entende de autopeças e ajuda na escolha certa.',
  },
  {
    icon: '🚚',
    title: 'Entrega nacional',
    desc: 'Enviamos para todo o Brasil com rastreamento e retirada na loja.',
  },
];

export default function ValuePillars() {
  return (
    <section className="pillars wrap" aria-label="Por que Galelugi">
      <div className="pillars-head">
        <span className="eyebrow">Por que Galelugi</span>
        <h2>Feita para quem precisa da peça certa, na hora certa</h2>
      </div>
      <div className="pillars-grid">
        {PILLARS.map((item) => (
          <article key={item.title} className="pillar-card">
            <span className="pillar-icon">{item.icon}</span>
            <h3>{item.title}</h3>
            <p>{item.desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

import { Link } from 'react-router-dom';

const CATEGORIES = [
  { icon: '⚙️', name: 'Motor' },
  { icon: '🛞', name: 'Freios' },
  { icon: '🔩', name: 'Suspensão' },
  { icon: '🌬️', name: 'Filtros' },
  { icon: '⚡', name: 'Elétrica' },
  { icon: '🚗', name: 'Carroceria' },
  { icon: '🔧', name: 'Transmissão' },
  { icon: '❄️', name: 'Arrefecimento' },
];

export default function CategoriesSection() {
  return (
    <section className="gl-categories">
      <p className="gl-section-label">Categorias</p>

      <div className="gl-categories__grid">
        {CATEGORIES.map((cat) => (
          <Link
            key={cat.name}
            to={`/pecas/?q=${encodeURIComponent(cat.name)}`}
            className="gl-category-card"
          >
            <span className="gl-category-card__icon">{cat.icon}</span>
            <span className="gl-category-card__name">{cat.name}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

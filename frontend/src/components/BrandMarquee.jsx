import { Link } from 'react-router-dom';
import { CAR_BRANDS } from '../utils/commerce';

export default function BrandMarquee() {
  const items = [...CAR_BRANDS, ...CAR_BRANDS];

  return (
    <section className="vehicle-strip wrap" aria-label="Buscar por montadora">
      <div className="vehicle-strip-head">
        <h3>Encontre por veículo</h3>
        <p>Selecione a montadora e veja peças compatíveis</p>
      </div>
      <div className="vehicle-marquee">
        <div className="vehicle-track">
          {items.map((brand, index) => (
            <Link
              key={`${brand.abbr}-${index}`}
              to={`/pecas/?q=${encodeURIComponent(brand.query)}`}
              className="vehicle-chip"
              style={{ '--brand-color': brand.color }}
            >
              <span className="vehicle-chip-logo">{brand.abbr}</span>
              {brand.name}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

import { Link } from 'react-router-dom';
import { Package, Search, Truck, Wrench, type LucideIcon } from 'lucide-react';
import { useStore } from '../../context/StoreContext';

type Feature = {
  icon: LucideIcon;
  title: string;
  text: string;
  href: string;
  external?: boolean;
};

export default function WhyUsSection() {
  const { whatsappUrl } = useStore();

  const features: Feature[] = [
    {
      icon: Search,
      title: 'Busca inteligente',
      text: 'Encontre por nome, código OEM, SKU ou compatibilidade de veículo. Resultados filtrados para o seu modelo.',
      href: '/pecas/',
    },
    {
      icon: Package,
      title: 'Estoque real',
      text: 'Só vendemos o que temos. Cada produto exibido tem disponibilidade confirmada em tempo real.',
      href: '/pecas/?in_stock=1',
    },
    {
      icon: Wrench,
      title: 'Especialistas',
      text: 'Equipe que entende de autopeças de verdade. Tire dúvidas antes de comprar via chat ou WhatsApp.',
      href: whatsappUrl,
      external: true,
    },
    {
      icon: Truck,
      title: 'Entrega nacional',
      text: 'Enviamos para todo o Brasil com rastreamento em tempo real e embalagem reforçada para peças frágeis.',
      href: '/prazos-entrega/',
    },
  ];

  return (
    <section className="gl-why-us">
      <div className="gl-why-us__inner">
        <p className="gl-section-label">Por que Galelugi</p>
        <h2 className="gl-why-us__title">
          Feita para quem precisa da peça certa, na hora certa
        </h2>
        <p className="gl-why-us__sub">
          Sem achismo, sem peça errada, sem tempo perdido.
        </p>

        <div className="gl-why-us__grid">
          {features.map(({ icon: Icon, title, text, href, external }) =>
            external ? (
              <a
                key={title}
                href={href}
                className="gl-feature-card"
                target="_blank"
                rel="noreferrer"
              >
                <div className="gl-feature-card__icon-wrap">
                  <Icon size={18} />
                </div>
                <h3 className="gl-feature-card__title">{title}</h3>
                <p className="gl-feature-card__text">{text}</p>
              </a>
            ) : (
              <Link key={title} to={href} className="gl-feature-card">
                <div className="gl-feature-card__icon-wrap">
                  <Icon size={18} />
                </div>
                <h3 className="gl-feature-card__title">{title}</h3>
                <p className="gl-feature-card__text">{text}</p>
              </Link>
            ),
          )}
        </div>
      </div>
    </section>
  );
}

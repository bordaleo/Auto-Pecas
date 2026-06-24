import { Link } from 'react-router-dom';

const BENEFITS = [
  {
    icon: '🚚',
    title: 'Frete grátis',
    desc: 'Em milhares de peças com envio rápido.',
    href: '/pecas/',
    cta: 'Mostrar produtos',
  },
  {
    icon: '👤',
    title: 'Entre na sua conta',
    desc: 'Aproveite ofertas para comprar tudo que quiser.',
    href: '/conta/perfil/',
    cta: 'Entrar na sua conta',
  },
  {
    icon: '📍',
    title: 'Insira sua localização',
    desc: 'Confira os custos e prazos de entrega.',
    href: '/pecas/',
    cta: 'Informar localização',
  },
  {
    icon: '💳',
    title: 'Meios de pagamento',
    desc: 'Pague com PIX, cartão ou boleto via Mercado Pago.',
    href: '/pecas/',
    cta: 'Mostrar meios',
  },
  {
    icon: '💰',
    title: 'Menos de R$100',
    desc: 'Confira produtos com preços baixos.',
    href: '/pecas/?q=',
    cta: 'Mostrar produtos',
  },
  {
    icon: '🔥',
    title: 'Mais vendidos',
    desc: 'Explore os produtos que são tendência.',
    href: '/pecas/?featured=1',
    cta: 'Ir para Mais vendidos',
  },
];

export default function BenefitsStrip() {
  return (
    <section className="benefits-strip wrap" aria-label="Benefícios">
      <div className="benefits-strip-track">
        {BENEFITS.map((item) => (
          <article key={item.title} className="benefit-tile">
            <div className="benefit-tile-icon">{item.icon}</div>
            <div className="benefit-tile-body">
              <h3>{item.title}</h3>
              <p>{item.desc}</p>
              <Link to={item.href}>{item.cta}</Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

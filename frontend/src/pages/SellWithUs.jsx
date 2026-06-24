import { Link, useOutletContext } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { formatCurrency } from '../api/client';

const BENEFITS = [
  {
    title: 'Alcance nacional',
    text: 'Publique peças e venda para oficinas e motoristas em todo o Brasil, sem montar site próprio.',
  },
  {
    title: 'Pagamento seguro',
    text: 'Checkout via Mercado Pago. Você recebe o repasse após cada venda aprovada.',
  },
  {
    title: 'Frete flexível',
    text: 'Envie do seu endereço ou deixe a Auto Peças Sandroni despachar por você (consignação).',
  },
  {
    title: 'Comissão transparente',
    text: 'Veja quanto você recebe antes de publicar cada peça. Sem taxas escondidas.',
  },
];

const STEPS = [
  { n: '1', title: 'Crie sua conta', text: 'Cadastro gratuito em poucos minutos.' },
  { n: '2', title: 'Abra sua loja', text: 'Informe CNPJ/CPF, CEP de origem e dados de contato.' },
  { n: '3', title: 'Publique peças', text: 'Foto real, compatibilidade com veículos e preço justo.' },
  { n: '4', title: 'Receba', text: 'Acompanhe pedidos e solicite repasse via PIX.' },
];

export default function SellWithUs() {
  const { config } = useStore();
  const { openAuth } = useOutletContext();
  const commission = config.marketplace_commission_percent || 12;
  const official = config.official_seller;
  const storeName = official?.store_name || config.store_name || 'Auto Peças Sandroni';

  return (
    <div className="sell-page wrap">
      <header className="sell-hero">
        <span className="eyebrow">Programa de parceiros</span>
        <h1>Venda suas peças na Galelugi</h1>
        <p>
          Oficinas, autopeças e revendedores: transforme estoque parado em receita.
          A <strong>{storeName}</strong> é a loja âncora — você vende junto, com a mesma confiança.
        </p>
        <div className="sell-hero-actions">
          <Link to="/vender/" className="btn btn-accent">Abrir minha loja</Link>
          <button type="button" className="btn btn-secondary" onClick={() => openAuth('register')}>
            Criar conta
          </button>
        </div>
      </header>

      <section className="sell-grid">
        {BENEFITS.map((item) => (
          <article key={item.title} className="sell-card">
            <h2>{item.title}</h2>
            <p>{item.text}</p>
          </article>
        ))}
      </section>

      <section className="sell-shipping">
        <h2>Como funciona o frete?</h2>
        <div className="sell-shipping-grid">
          <article className="sell-shipping-card">
            <span className="sell-shipping-tag">Opção A</span>
            <h3>Envio próprio</h3>
            <p>
              Você cadastra seu CEP de origem. O frete é calculado automaticamente
              (Melhor Envio ou tabela) e o cliente paga na compra.
            </p>
          </article>
          <article className="sell-shipping-card sell-shipping-card--highlight">
            <span className="sell-shipping-tag">Opção B · Recomendado no início</span>
            <h3>Envio pela {storeName}</h3>
            <p>
              Deixe a peça na Sandroni (consignação). Ela embala e envia para o cliente.
              Você foca em estoque e preço — nós cuidamos da logística.
            </p>
          </article>
        </div>
      </section>

      <section className="sell-steps">
        <h2>Comece em 4 passos</h2>
        <div className="sell-steps-grid">
          {STEPS.map((step) => (
            <article key={step.n} className="sell-step">
              <span className="sell-step-num">{step.n}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="sell-cta">
        <h2>Pronto para vender?</h2>
        <p>
          Comissão Galelugi: <strong>{commission}%</strong> por venda ·
          Frete grátis para compradores acima de {formatCurrency(config.free_shipping_min || 299)}
        </p>
        <Link to="/vender/" className="btn btn-accent btn-lg">Cadastrar minha loja agora</Link>
        {official?.slug && (
          <p className="sell-cta-note">
            Conheça a loja oficial:{' '}
            <Link to={`/loja/${official.slug}/`}>{official.store_name}</Link>
          </p>
        )}
      </section>
    </div>
  );
}

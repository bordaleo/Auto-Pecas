import { Link } from 'react-router-dom';
import { useStore } from '../context/StoreContext';
import { formatCurrency } from '../api/client';

const STEPS = [
  {
    n: '01',
    title: 'Busque a peça certa',
    text: 'Use OEM, SKU, marca ou veículo compatível. Compare ofertas de vendedores verificados.',
  },
  {
    n: '02',
    title: 'Compre com segurança',
    text: 'Pagamento via Mercado Pago (PIX, cartão ou boleto). Frete calculado pelo CEP.',
  },
  {
    n: '03',
    title: 'Acompanhe o envio',
    text: 'Rastreio visível em Meus pedidos. Suporte pelo WhatsApp se tiver dúvida de compatibilidade.',
  },
  {
    n: '04',
    title: 'Venda também',
    text: 'Abra sua loja, publique com foto real e receba após cada venda, com comissão transparente.',
  },
];

export default function HowItWorks() {
  const { config } = useStore();
  const commission = config.marketplace_commission_percent || 8;
  const freeMin = Number(config.free_shipping_min || 299);

  return (
    <div className="how-page wrap">
      <header className="how-hero">
        <span className="eyebrow">Como funciona</span>
        <h1>Marketplace de autopeças feito para comprar e vender com confiança</h1>
        <p>
          Na Galelugi, mecânicos, revendedores e motoristas encontram peças reais —
          e quem tem estoque pode vender para todo o Brasil.
        </p>
      </header>

      <section className="how-steps">
        {STEPS.map((step) => (
          <article key={step.n} className="how-step-card">
            <span className="how-step-num">{step.n}</span>
            <h2>{step.title}</h2>
            <p>{step.text}</p>
          </article>
        ))}
      </section>

      <section className="how-grid">
        <article className="how-info-card">
          <h3>Para compradores</h3>
          <ul>
            <li>Frete grátis em pedidos acima de {formatCurrency(freeMin)}</li>
            <li>Parcelamento em até 12x sem juros</li>
            <li>Cupom <strong>BEMVINDO10</strong> na primeira compra (10% off)</li>
            <li>Rastreio do pedido em tempo real</li>
          </ul>
          <Link to="/pecas/" className="btn btn-accent">Ver catálogo</Link>
        </article>
        <article className="how-info-card how-info-card--seller">
          <h3>Para vendedores</h3>
          <ul>
            <li>Cadastro gratuito da loja</li>
            <li>Comissão Galelugi: {commission}% por venda</li>
            <li>Preview do valor líquido antes de publicar</li>
            <li>Foto real obrigatória em cada anúncio</li>
          </ul>
          <Link to="/venda-conosco/" className="btn btn-secondary">Começar a vender</Link>
        </article>
      </section>

      <section className="how-trust">
        <h2>Compra protegida</h2>
        <p>
          Pagamento processado pelo Mercado Pago. Pedidos aprovados geram confirmação por e-mail.
          Dúvida sobre compatibilidade? Fale com o vendedor ou nosso suporte pelo WhatsApp.
        </p>
      </section>
    </div>
  );
}

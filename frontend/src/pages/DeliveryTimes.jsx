import InternalPage from '../components/InternalPage';
import PageSeo from '../components/PageSeo';
import { useStore } from '../context/StoreContext';
import { formatCurrency } from '../api/client';

const REGIONS = [
  { region: 'Sudeste (SP capital)', days: '2–5 dias úteis', note: 'Correios PAC ou transportadora parceira' },
  { region: 'Sudeste (interior)', days: '3–7 dias úteis', note: 'Prazo após postagem' },
  { region: 'Sul', days: '4–8 dias úteis', note: 'Rastreio disponível em Meus pedidos' },
  { region: 'Centro-Oeste', days: '5–10 dias úteis', note: 'Prazo estimado' },
  { region: 'Nordeste', days: '6–12 dias úteis', note: 'Prazo estimado' },
  { region: 'Norte', days: '8–15 dias úteis', note: 'Prazo estimado' },
];

export default function DeliveryTimes() {
  const { config } = useStore();
  const freeMin = Number(config.free_shipping_min || 299);

  return (
    <>
      <PageSeo
        title="Prazos de entrega | Galelugi Peças"
        description="Prazos de entrega por região, frete grátis e retirada na loja Galelugi."
      />
      <InternalPage
        title="Prazos de entrega"
        subtitle={`Frete grátis em pedidos acima de ${formatCurrency(freeMin)}. Retirada na loja sem custo.`}
      >
        <section>
          <h2>Como calculamos o frete</h2>
          <p>
            O valor e prazo são estimados pelo CEP no carrinho ou checkout. Após o pagamento aprovado,
            você acompanha o rastreio em <strong>Meus pedidos</strong>.
          </p>
        </section>
        <section>
          <h2>Prazos por região (após postagem)</h2>
          <div className="info-table">
            {REGIONS.map((row) => (
              <div key={row.region} className="info-table-row">
                <strong>{row.region}</strong>
                <span>{row.days}</span>
                <small>{row.note}</small>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h2>Retirada na loja</h2>
          <p>
            Escolha <strong>Retirada na loja</strong> no checkout. Endereço: {config.store_address || 'consulte o suporte'}.
            A peça fica disponível após confirmação do pagamento — avisamos por e-mail.
          </p>
        </section>
      </InternalPage>
    </>
  );
}

import InternalPage from '../components/InternalPage';
import PageSeo from '../components/PageSeo';
import ReturnRequestPanel from '../components/ReturnRequestPanel';

export default function ReturnsPolicy() {
  return (
    <>
      <PageSeo
        title="Trocas e devoluções | Galelugi Peças"
        description="Política de troca e devolução de autopeças na Galelugi. Prazos, condições e como solicitar."
      />
      <InternalPage
        title="Trocas e devoluções"
        subtitle="Compre com tranquilidade — saiba quando e como trocar sua peça."
      >
        <section className="return-policy-action">
          <ReturnRequestPanel />
        </section>

        <section>
          <h2>7 dias para arrependimento</h2>
          <p>
            Você pode desistir da compra em até <strong>7 dias corridos</strong> após o recebimento,
            conforme o Código de Defesa do Consumidor, desde que a peça esteja na embalagem original,
            sem sinais de uso ou instalação.
          </p>
        </section>
        <section>
          <h2>Peça errada ou com defeito</h2>
          <p>
            Se a peça não for compatível com seu veículo (divergência de OEM/código) ou apresentar defeito
            de fabricação, solicite pelo formulário acima em até <strong>30 dias</strong> com fotos e número do pedido.
            Analisamos e orientamos troca ou reembolso.
          </p>
        </section>
        <section>
          <h2>Como funciona</h2>
          <ol>
            <li>Selecione o item e o motivo no formulário no topo desta página.</li>
            <li>Aguarde a análise do vendedor (até 2 dias úteis).</li>
            <li>Se aprovado, envie a peça conforme instruções ou receba reembolso via Mercado Pago.</li>
          </ol>
        </section>
        <section>
          <h2>Reembolso</h2>
          <p>
            Após aprovação, o reembolso é processado pelo Mercado Pago no mesmo meio de pagamento.
            O prazo de estorno depende da operadora ou banco (geralmente 5 a 15 dias úteis).
          </p>
        </section>
      </InternalPage>
    </>
  );
}

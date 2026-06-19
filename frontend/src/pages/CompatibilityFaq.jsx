import { Link } from 'react-router-dom';
import InternalPage from '../components/InternalPage';
import PageSeo from '../components/PageSeo';
import { useStore } from '../context/StoreContext';

const FAQ = [
  {
    q: 'Como saber se a peça serve no meu carro?',
    a: 'Confira o campo "Compatível" na página do produto e o código OEM. Em caso de dúvida, use o botão WhatsApp na página da peça com o modelo e ano do veículo.',
  },
  {
    q: 'O que é código OEM?',
    a: 'É o código do fabricante original (ex.: 51605-TBA-A01). Busque por OEM na barra de pesquisa para encontrar equivalentes.',
  },
  {
    q: 'Peça paralela ou original?',
    a: 'No anúncio informamos marca e tipo. Vendedores cadastram fotos reais e descrição técnica. Dúvidas? Fale com o vendedor ou suporte.',
  },
  {
    q: 'Posso combinar peças de vendedores diferentes?',
    a: 'Sim. O carrinho aceita itens de várias lojas. O frete é calculado sobre o subtotal total do pedido.',
  },
  {
    q: 'E se eu errar a peça?',
    a: 'Consulte nossa política de trocas. Peça sem instalação pode ser devolvida em até 7 dias (CDC).',
  },
];

export default function CompatibilityFaq() {
  const { whatsappUrl } = useStore();

  return (
    <>
      <PageSeo
        title="FAQ — Compatibilidade de peças | Galelugi Peças"
        description="Dúvidas sobre OEM, compatibilidade de veículos e como escolher a peça certa na Galelugi."
      />
      <InternalPage
        title="FAQ de compatibilidade"
        subtitle="Respostas rápidas para comprar a peça certa."
      >
        <div className="faq-list">
          {FAQ.map((item) => (
            <details key={item.q} className="faq-item">
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
        <p className="faq-cta">
          Ainda com dúvida?{' '}
          <a href={whatsappUrl} target="_blank" rel="noreferrer">Fale no WhatsApp</a>
          {' '}ou veja o <Link to="/como-funciona/">Como funciona</Link>.
        </p>
      </InternalPage>
    </>
  );
}

import { Link } from 'react-router-dom';
import { useStore } from '../../context/StoreContext';
import Logo from '../Logo';

export default function Footer({ onOpenAuth }) {
  const { config, whatsappUrl } = useStore();

  return (
    <footer className="site-footer">
      <div className="footer-cta wrap">
        <div>
          <h3>Precisa de ajuda para encontrar a peça?</h3>
          <p>Fale com nosso time pelo WhatsApp — especialistas em autopeças.</p>
        </div>
        <a href={whatsappUrl} className="btn btn-accent" target="_blank" rel="noreferrer">
          Chamar no WhatsApp
        </a>
      </div>

      <div className="wrap footer-grid">
        <div className="footer-brand">
          <Logo />
          <p>
            Galelugi é o marketplace de autopeças feito para mecânicos, revendedores
            e motoristas que não podem errar na hora de comprar.
          </p>
        </div>

        <div className="footer-col">
          <h4>Loja</h4>
          <ul>
            <li><Link to="/pecas/">Catálogo</Link></li>
            <li><Link to="/como-funciona/">Como funciona</Link></li>
            <li><Link to="/pecas/?featured=1">Destaques</Link></li>
            <li><Link to="/conta/pedidos/">Meus pedidos</Link></li>
            <li><Link to="/conta/solicitacoes/">Pedido de peça</Link></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Conta</h4>
          <ul>
            <li><Link to="/conta/">Minha conta</Link></li>
            <li>
              <button type="button" className="footer-btn" onClick={() => onOpenAuth('login')}>
                Entrar / Cadastrar
              </button>
            </li>
            <li><Link to="/vender/">Vender na Galelugi</Link></li>
            <li><Link to="/gerenciar/">Área do lojista</Link></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Ajuda</h4>
          <ul>
            <li><Link to="/faq-compatibilidade/">FAQ compatibilidade</Link></li>
            <li><Link to="/prazos-entrega/">Prazos de entrega</Link></li>
            <li><Link to="/trocas-devolucoes/">Trocas e devoluções</Link></li>
            <li><Link to="/como-funciona/">Como funciona</Link></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Contato</h4>
          <ul>
            <li><a href={whatsappUrl} target="_blank" rel="noreferrer">WhatsApp</a></li>
            {config.store_phone && <li>{config.store_phone}</li>}
            {config.store_address && <li>{config.store_address}</li>}
          </ul>
        </div>
      </div>

      <div className="footer-base wrap">
        <p>© {new Date().getFullYear()} {config.store_name || 'Galelugi Peças'}. Todos os direitos reservados.</p>
        <p className="footer-pay">PIX · Cartão · Boleto via Mercado Pago</p>
      </div>
    </footer>
  );
}

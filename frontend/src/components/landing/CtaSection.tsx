import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useStore } from '../../context/StoreContext';

export default function CtaSection() {
  const { whatsappUrl } = useStore();

  return (
    <section className="gl-cta-section">
      <div className="gl-cta-box">
        <h2 className="gl-cta-box__title">Pronto para encontrar sua peça?</h2>
        <p className="gl-cta-box__text">
          Use o código BEMVINDO10 e ganhe 10% off na primeira compra.
        </p>
        <div className="gl-cta-box__actions">
          <Link to="/pecas/" className="gl-btn gl-btn--primary">
            Começar agora
            <ArrowRight size={16} />
          </Link>
          <a
            href={whatsappUrl}
            className="gl-btn gl-btn--ghost"
            target="_blank"
            rel="noreferrer"
          >
            Falar com especialista
          </a>
        </div>
      </div>
    </section>
  );
}

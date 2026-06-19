import { useState } from 'react';
import { formatCurrency } from '../api/client';

export default function PixPaymentPanel({ amount, qrCode, qrCodeBase64, onCopy }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!qrCode) return;
    try {
      await navigator.clipboard.writeText(qrCode);
      setCopied(true);
      onCopy?.();
      setTimeout(() => setCopied(false), 2500);
    } catch {
      /* fallback silencioso */
    }
  };

  return (
    <div className="pix-payment-panel">
      <h3>Pague com PIX</h3>
      <p className="pix-payment-hint">
        Escaneie o QR Code ou copie o código. Valor: <strong>{formatCurrency(amount)}</strong>
      </p>

      {qrCodeBase64 && (
        <div className="pix-qr-wrap">
          <img
            src={`data:image/png;base64,${qrCodeBase64}`}
            alt="QR Code PIX"
            className="pix-qr-image"
          />
        </div>
      )}

      {qrCode && (
        <div className="pix-copy-block">
          <label className="pix-copy-label">Pix copia e cola</label>
          <textarea
            readOnly
            value={qrCode}
            rows={4}
            className="pix-copy-code"
            onFocus={(e) => e.target.select()}
          />
          <button type="button" className="btn btn-accent btn-full" onClick={handleCopy}>
            {copied ? 'Código copiado!' : 'Copiar código PIX'}
          </button>
        </div>
      )}

      <p className="form-hint pix-wait-hint">
        Aguardando confirmação do pagamento… Esta página atualiza automaticamente.
      </p>
    </div>
  );
}

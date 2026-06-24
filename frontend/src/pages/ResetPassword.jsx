import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import OtpInput, { OTP_LENGTH } from '../components/OtpInput';
import PageSeo from '../components/PageSeo';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

const RESEND_COOLDOWN = 60;

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { forgotPassword, resetPassword } = useAuth();
  const { showToast } = useToast();

  const [step, setStep] = useState(searchParams.get('code') ? 'confirm' : 'email');
  const [email, setEmail] = useState(searchParams.get('email') || '');
  const [otpCode, setOtpCode] = useState(searchParams.get('code') || '');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [message, setMessage] = useState({ text: '', error: false });
  const [submitting, setSubmitting] = useState(false);
  const [resendSeconds, setResendSeconds] = useState(0);

  useEffect(() => {
    if (resendSeconds <= 0) return undefined;
    const timer = setInterval(() => setResendSeconds((s) => s - 1), 1000);
    return () => clearInterval(timer);
  }, [resendSeconds]);

  const sendCode = async (event) => {
    event?.preventDefault();
    if (!email.trim()) {
      setMessage({ text: 'Informe seu email.', error: true });
      return;
    }
    setSubmitting(true);
    setMessage({ text: '', error: false });
    try {
      await forgotPassword(email.trim());
      setResendSeconds(RESEND_COOLDOWN);
      setStep('confirm');
      setMessage({
        text: 'Se o email estiver cadastrado, você receberá um código de 4 dígitos. Verifique também o spam.',
        error: false,
      });
    } catch (error) {
      setMessage({ text: error.message, error: true });
    } finally {
      setSubmitting(false);
    }
  };

  const submitReset = async (codeOverride) => {
    const code = (codeOverride || otpCode).trim();
    if (code.length !== OTP_LENGTH) {
      setMessage({ text: 'Digite os 4 dígitos do código.', error: true });
      return;
    }
    if (password.length < 6) {
      setMessage({ text: 'A senha deve ter no mínimo 6 caracteres.', error: true });
      return;
    }
    if (password !== passwordConfirm) {
      setMessage({ text: 'As senhas não coincidem.', error: true });
      return;
    }
    setSubmitting(true);
    setMessage({ text: '', error: false });
    try {
      await resetPassword(code, password, passwordConfirm);
      showToast('Senha redefinida! Bem-vindo de volta.');
      navigate('/');
    } catch (error) {
      setMessage({ text: error.message, error: true });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async (event) => {
    event.preventDefault();
    await submitReset();
  };

  const handleResend = async () => {
    if (!email.trim() || resendSeconds > 0) return;
    try {
      await forgotPassword(email.trim());
      setResendSeconds(RESEND_COOLDOWN);
      setMessage({ text: 'Novo código enviado. Verifique também o spam.', error: false });
    } catch (error) {
      setMessage({ text: error.message, error: true });
    }
  };

  return (
    <>
      <PageSeo title="Redefinir senha | Galelugi Peças" description="Recupere o acesso à sua conta." />
      <div className="wrap internal-page">
        <div className="internal-page-card auth-standalone" style={{ maxWidth: 440, margin: '2rem auto' }}>
          <h1>Redefinir senha</h1>
          <p className="auth-step-hint">
            {step === 'email' ? 'Passo 1 de 2 — informe seu email' : 'Passo 2 de 2 — código e nova senha'}
          </p>

          {step === 'email' && (
            <form onSubmit={sendCode}>
              <div className="form-group">
                <label htmlFor="reset-email">Email da conta</label>
                <input
                  id="reset-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Enviando...' : 'Enviar código'}
              </button>
            </form>
          )}

          {step === 'confirm' && (
            <form onSubmit={handleReset}>
              <p className="auth-verify-intro">
                Digite o código enviado para <strong>{email || 'seu email'}</strong>
              </p>
              <div className="form-group">
                <label>Código de verificação</label>
                <OtpInput value={otpCode} onChange={setOtpCode} onComplete={submitReset} />
              </div>
              <div className="form-group">
                <label htmlFor="reset-password">Nova senha</label>
                <input
                  id="reset-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={6}
                  required
                  autoComplete="new-password"
                />
              </div>
              <div className="form-group">
                <label htmlFor="reset-confirm">Confirmar nova senha</label>
                <input
                  id="reset-confirm"
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  minLength={6}
                  required
                  autoComplete="new-password"
                />
              </div>
              <p className="auth-spam-hint">
                Não recebeu o código?{' '}
                <button type="button" className="btn-link" disabled={resendSeconds > 0} onClick={handleResend}>
                  {resendSeconds > 0 ? `Reenviar em ${resendSeconds}s` : 'Reenviar código'}
                </button>
              </p>
              <button
                type="submit"
                className="btn btn-primary btn-full"
                disabled={submitting || otpCode.length !== OTP_LENGTH}
              >
                {submitting ? 'Salvando...' : 'Redefinir senha'}
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-full"
                style={{ marginTop: '0.5rem' }}
                onClick={() => setStep('email')}
              >
                Voltar
              </button>
            </form>
          )}

          {message.text && (
            <p className={`form-msg${message.error ? ' error' : ' ok'}`}>{message.text}</p>
          )}

          <p style={{ marginTop: '1.25rem', fontSize: '0.9rem' }}>
            <Link to="/">Voltar à loja</Link>
          </p>
        </div>
      </div>
    </>
  );
}

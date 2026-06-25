import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import OtpInput, { OTP_LENGTH } from './OtpInput';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

const RESEND_COOLDOWN = 60;

export default function AuthModal({ open, tab: initialTab, onClose, onTabChange }) {
  const [tab, setTab] = useState(initialTab || 'login');
  const [message, setMessage] = useState({ text: '', error: false });
  const [pendingEmail, setPendingEmail] = useState(localStorage.getItem('pending_verify_email') || '');
  const [resetEmail, setResetEmail] = useState('');
  const [resetStep, setResetStep] = useState('email');
  const [otpCode, setOtpCode] = useState('');
  const [resetOtp, setResetOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [resendSeconds, setResendSeconds] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const { login, register, verifyEmail, resendVerification, forgotPassword, resetPassword } = useAuth();
  const { showToast } = useToast();

  useEffect(() => {
    if (resendSeconds <= 0) return undefined;
    const timer = setInterval(() => setResendSeconds((s) => s - 1), 1000);
    return () => clearInterval(timer);
  }, [resendSeconds]);

  useEffect(() => {
    if (open && initialTab) setTab(initialTab);
  }, [open, initialTab]);

  if (!open) return null;

  const switchTab = (next) => {
    setTab(next);
    onTabChange?.(next);
    setMessage({ text: '', error: false });
    setOtpCode('');
    setResetOtp('');
    setNewPassword('');
    setNewPasswordConfirm('');
    if (next !== 'reset') setResetStep('email');
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await login(form.get('email'), form.get('password'));
      onClose();
      showToast('Bem-vindo à Galelugi Peças!');
    } catch (error) {
      if (error.message?.includes('não foi verificada')) {
        setPendingEmail(form.get('email'));
        localStorage.setItem('pending_verify_email', form.get('email'));
        switchTab('verify');
      }
      setMessage({ text: error.message, error: true });
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const password = form.get('password');
    const confirm = form.get('password_confirm');
    if (password !== confirm) {
      setMessage({ text: 'As senhas não coincidem.', error: true });
      return;
    }
    setSubmitting(true);
    try {
      const data = await register({
        name: form.get('name'),
        email: form.get('email'),
        password,
        password_confirm: confirm,
      });
      if (data.access_token) {
        onClose();
        showToast('Conta criada! Bem-vindo à Galelugi Peças.');
        return;
      }
      const email = form.get('email');
      localStorage.setItem('pending_verify_email', email);
      setPendingEmail(email);
      setResendSeconds(RESEND_COOLDOWN);
      switchTab('verify');
      setMessage({
        text: 'Enviamos um código de 4 dígitos. Se não aparecer em alguns minutos, verifique o spam.',
        error: false,
      });
    } catch (error) {
      setMessage({ text: error.message, error: true });
    } finally {
      setSubmitting(false);
    }
  };

  const submitVerification = async (code) => {
    if (!code || code.length !== OTP_LENGTH) {
      setMessage({ text: 'Digite os 4 dígitos do código.', error: true });
      return;
    }
    setSubmitting(true);
    try {
      await verifyEmail(pendingEmail, code);
      localStorage.removeItem('pending_verify_email');
      onClose();
      showToast('Conta ativada! Bem-vindo à Galelugi Peças.');
    } catch (error) {
      setMessage({ text: error.message, error: true });
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async (event) => {
    event.preventDefault();
    await submitVerification(otpCode);
  };

  const handleResend = async () => {
    if (!pendingEmail || resendSeconds > 0) return;
    try {
      await resendVerification(pendingEmail);
      setResendSeconds(RESEND_COOLDOWN);
      setMessage({
        text: 'Novo código enviado. Verifique também a pasta de spam.',
        error: false,
      });
    } catch (error) {
      setMessage({ text: error.message, error: true });
    }
  };

  const startReset = () => {
    const email = document.querySelector('#login-email')?.value || '';
    setResetEmail(email);
    setResetStep('email');
    switchTab('reset');
  };

  const sendResetCode = async (event) => {
    event.preventDefault();
    if (!resetEmail.trim()) {
      setMessage({ text: 'Informe seu email.', error: true });
      return;
    }
    setSubmitting(true);
    try {
      await forgotPassword(resetEmail.trim());
      setResendSeconds(RESEND_COOLDOWN);
      setResetStep('confirm');
      setMessage({
        text: 'Se o email estiver cadastrado, você receberá um código. Verifique também o spam.',
        error: false,
      });
    } catch (error) {
      setMessage({ text: error.message, error: true });
    } finally {
      setSubmitting(false);
    }
  };

  const submitPasswordReset = async (codeOverride) => {
    const code = (codeOverride || resetOtp).trim();
    if (code.length !== OTP_LENGTH) {
      setMessage({ text: 'Digite os 4 dígitos do código.', error: true });
      return;
    }
    if (newPassword.length < 6) {
      setMessage({ text: 'A senha deve ter no mínimo 6 caracteres.', error: true });
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      setMessage({ text: 'As senhas não coincidem.', error: true });
      return;
    }
    setSubmitting(true);
    try {
      await resetPassword(code, newPassword, newPasswordConfirm);
      onClose();
      showToast('Senha redefinida! Bem-vindo de volta.');
    } catch (error) {
      setMessage({ text: error.message, error: true });
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetSubmit = async (event) => {
    event.preventDefault();
    await submitPasswordReset();
  };

  const handleResetResend = async () => {
    if (!resetEmail.trim() || resendSeconds > 0) return;
    try {
      await forgotPassword(resetEmail.trim());
      setResendSeconds(RESEND_COOLDOWN);
      setMessage({ text: 'Novo código enviado.', error: false });
    } catch (error) {
      setMessage({ text: error.message, error: true });
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal auth-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Autenticação">
        <div className="modal-header">
          <strong>
            {tab === 'register' && 'Criar conta'}
            {tab === 'verify' && 'Confirme seu email'}
            {tab === 'reset' && 'Redefinir senha'}
            {tab === 'login' && 'Entre na sua conta'}
          </strong>
          <button type="button" className="btn-ghost" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {tab === 'login' && (
            <div className="tabs">
              <button type="button" className="tab active">Entrar</button>
              <button type="button" className="tab" onClick={() => switchTab('register')}>Criar conta</button>
            </div>
          )}
          {tab === 'register' && (
            <div className="tabs">
              <button type="button" className="tab" onClick={() => switchTab('login')}>Entrar</button>
              <button type="button" className="tab active">Criar conta</button>
            </div>
          )}

          {tab === 'login' && (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label htmlFor="login-email">Email ou usuário</label>
                <input
                  id="login-email"
                  name="email"
                  type="text"
                  required
                  autoComplete="username"
                  placeholder="sandroni, sandroni@sandroni ou sandroni@sandroni.com"
                />
              </div>
              <div className="form-group">
                <label htmlFor="login-password">Senha</label>
                <input id="login-password" name="password" type="password" required />
              </div>
              <button type="button" className="btn-ghost btn-sm" onClick={startReset} style={{ marginBottom: '0.5rem' }}>
                Esqueci minha senha
              </button>
              <button type="submit" className="btn btn-primary btn-full">Entrar</button>
            </form>
          )}

          {tab === 'register' && (
            <form onSubmit={handleRegister}>
              <p className="auth-step-hint">Passo 1 de 2 — seus dados</p>
              <div className="form-group">
                <label htmlFor="reg-name">Nome completo</label>
                <input id="reg-name" name="name" required autoComplete="name" />
              </div>
              <div className="form-group">
                <label htmlFor="reg-email">Email</label>
                <input id="reg-email" name="email" type="email" required autoComplete="email" />
              </div>
              <div className="form-group">
                <label htmlFor="reg-password">Senha</label>
                <input id="reg-password" name="password" type="password" required minLength={6} autoComplete="new-password" />
              </div>
              <div className="form-group">
                <label htmlFor="reg-confirm">Confirmar senha</label>
                <input id="reg-confirm" name="password_confirm" type="password" required autoComplete="new-password" />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Criando conta...' : 'Continuar'}
              </button>
            </form>
          )}

          {tab === 'verify' && (
            <form onSubmit={handleVerify}>
              <p className="auth-step-hint">Passo 2 de 2 — confirmação</p>
              <p className="auth-verify-intro">
                Enviamos um código de <strong>4 dígitos</strong> para<br />
                <strong>{pendingEmail}</strong>
              </p>
              <div className="form-group">
                <label>Digite o código</label>
                <OtpInput value={otpCode} onChange={setOtpCode} onComplete={submitVerification} />
              </div>
              <p className="auth-spam-hint">
                Não recebeu? Verifique spam ou lixo eletrônico.
                {' '}
                <button type="button" className="btn-link" disabled={resendSeconds > 0} onClick={handleResend}>
                  {resendSeconds > 0 ? `Reenviar em ${resendSeconds}s` : 'Reenviar código'}
                </button>
              </p>
              <button type="submit" className="btn btn-primary btn-full" disabled={submitting || otpCode.length !== OTP_LENGTH}>
                {submitting ? 'Verificando...' : 'Ativar conta'}
              </button>
              <button type="button" className="btn btn-ghost btn-full" style={{ marginTop: '0.5rem' }} onClick={() => switchTab('register')}>
                Voltar
              </button>
            </form>
          )}

          {tab === 'reset' && resetStep === 'email' && (
            <form onSubmit={sendResetCode}>
              <p className="auth-step-hint">Passo 1 de 2 — seu email</p>
              <div className="form-group">
                <label htmlFor="reset-modal-email">Email da conta</label>
                <input
                  id="reset-modal-email"
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Enviando...' : 'Enviar código'}
              </button>
              <button type="button" className="btn btn-ghost btn-full" style={{ marginTop: '0.5rem' }} onClick={() => switchTab('login')}>
                Voltar ao login
              </button>
            </form>
          )}

          {tab === 'reset' && resetStep === 'confirm' && (
            <form onSubmit={handleResetSubmit}>
              <p className="auth-step-hint">Passo 2 de 2 — nova senha</p>
              <p className="auth-verify-intro">
                Código enviado para <strong>{resetEmail}</strong>
              </p>
              <div className="form-group">
                <label>Código</label>
                <OtpInput value={resetOtp} onChange={setResetOtp} onComplete={submitPasswordReset} />
              </div>
              <div className="form-group">
                <label htmlFor="modal-new-password">Nova senha</label>
                <input
                  id="modal-new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  minLength={6}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="modal-new-confirm">Confirmar senha</label>
                <input
                  id="modal-new-confirm"
                  type="password"
                  value={newPasswordConfirm}
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                  minLength={6}
                  required
                />
              </div>
              <p className="auth-spam-hint">
                <button type="button" className="btn-link" disabled={resendSeconds > 0} onClick={handleResetResend}>
                  {resendSeconds > 0 ? `Reenviar em ${resendSeconds}s` : 'Reenviar código'}
                </button>
              </p>
              <button type="submit" className="btn btn-primary btn-full" disabled={submitting || resetOtp.length !== OTP_LENGTH}>
                {submitting ? 'Salvando...' : 'Redefinir senha'}
              </button>
              <button type="button" className="btn btn-ghost btn-full" style={{ marginTop: '0.5rem' }} onClick={() => setResetStep('email')}>
                Voltar
              </button>
            </form>
          )}

          {message.text && (
            <p className={`form-msg${message.error ? ' error' : ' ok'}`}>{message.text}</p>
          )}

          {tab === 'login' && (
            <p className="auth-spam-hint" style={{ marginTop: '0.75rem' }}>
              Ou acesse <Link to="/reset-password" onClick={onClose}>a página de recuperação</Link>.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

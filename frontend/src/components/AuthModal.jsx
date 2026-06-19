import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

const OTP_LENGTH = 4;
const RESEND_COOLDOWN = 60;

function OtpInput({ value, onChange, onComplete }) {
  const inputsRef = useRef([]);

  const digits = value.padEnd(OTP_LENGTH, ' ').split('').slice(0, OTP_LENGTH);

  const updateAt = (index, char) => {
    const next = digits.map((d, i) => (i === index ? char : d)).join('').replace(/ /g, '');
    onChange(next.slice(0, OTP_LENGTH));
    if (char && index < OTP_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus();
    }
    if (next.length === OTP_LENGTH) {
      onComplete?.(next);
    }
  };

  const handleChange = (index, event) => {
    const raw = event.target.value.replace(/\D/g, '');
    if (!raw) {
      updateAt(index, '');
      return;
    }
    if (raw.length > 1) {
      const merged = `${value}${raw}`.replace(/\D/g, '').slice(0, OTP_LENGTH);
      onChange(merged);
      const focusIndex = Math.min(merged.length, OTP_LENGTH - 1);
      inputsRef.current[focusIndex]?.focus();
      if (merged.length === OTP_LENGTH) onComplete?.(merged);
      return;
    }
    updateAt(index, raw);
  };

  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !digits[index]?.trim() && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handlePaste = (event) => {
    event.preventDefault();
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
    onChange(pasted);
    if (pasted.length === OTP_LENGTH) onComplete?.(pasted);
    inputsRef.current[Math.min(pasted.length, OTP_LENGTH - 1)]?.focus();
  };

  return (
    <div className="otp-inputs" onPaste={handlePaste}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => { inputsRef.current[index] = el; }}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          maxLength={1}
          value={digit.trim()}
          aria-label={`Dígito ${index + 1}`}
          onChange={(e) => handleChange(index, e)}
          onKeyDown={(e) => handleKeyDown(index, e)}
        />
      ))}
    </div>
  );
}

export default function AuthModal({ open, tab: initialTab, onClose, onTabChange }) {
  const [tab, setTab] = useState(initialTab || 'login');
  const [message, setMessage] = useState({ text: '', error: false });
  const [pendingEmail, setPendingEmail] = useState(localStorage.getItem('pending_verify_email') || '');
  const [otpCode, setOtpCode] = useState('');
  const [resendSeconds, setResendSeconds] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const { login, register, verifyEmail, resendVerification } = useAuth();
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

  const handleForgot = async () => {
    const email = document.querySelector('#login-email')?.value;
    if (!email) {
      setMessage({ text: 'Informe seu email', error: true });
      return;
    }
    try {
      await api('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) });
      showToast('Código enviado! Verifique também o spam.');
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
            {tab === 'login' && 'Entre na sua conta'}
          </strong>
          <button type="button" className="btn-ghost" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {tab !== 'verify' && (
            <div className="tabs">
              <button type="button" className={`tab${tab === 'login' ? ' active' : ''}`} onClick={() => switchTab('login')}>Entrar</button>
              <button type="button" className={`tab${tab === 'register' ? ' active' : ''}`} onClick={() => switchTab('register')}>Criar conta</button>
            </div>
          )}

          {tab === 'login' && (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label htmlFor="login-email">Email</label>
                <input id="login-email" name="email" type="email" required />
              </div>
              <div className="form-group">
                <label htmlFor="login-password">Senha</label>
                <input id="login-password" name="password" type="password" required />
              </div>
              <button type="button" className="btn-ghost btn-sm" onClick={handleForgot} style={{ marginBottom: '1rem' }}>
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
                <OtpInput
                  value={otpCode}
                  onChange={setOtpCode}
                  onComplete={submitVerification}
                />
              </div>
              <p className="auth-spam-hint">
                Não recebeu? Verifique spam ou lixo eletrônico.
                {' '}
                <button
                  type="button"
                  className="btn-link"
                  disabled={resendSeconds > 0}
                  onClick={handleResend}
                >
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

          {message.text && (
            <p className={`form-msg${message.error ? ' error' : ' ok'}`}>{message.text}</p>
          )}
        </div>
      </div>
    </div>
  );
}

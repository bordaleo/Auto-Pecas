import { useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export default function AuthModal({ open, tab: initialTab, onClose, onTabChange }) {
  const [tab, setTab] = useState(initialTab || 'login');
  const [message, setMessage] = useState({ text: '', error: false });
  const [pendingEmail, setPendingEmail] = useState(localStorage.getItem('pending_verify_email') || '');
  const { login, register, verifyEmail } = useAuth();
  const { showToast } = useToast();

  if (!open) return null;

  const switchTab = (next) => {
    setTab(next);
    onTabChange?.(next);
    setMessage({ text: '', error: false });
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await login(form.get('email'), form.get('password'));
      onClose();
      showToast('Bem-vindo à Galelugi Peças!');
    } catch (error) {
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
      localStorage.setItem('pending_verify_email', form.get('email'));
      setPendingEmail(form.get('email'));
      switchTab('verify');
      setMessage({ text: 'Código enviado para seu email.', error: false });
    } catch (error) {
      setMessage({ text: error.message, error: true });
    }
  };

  const handleVerify = async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await verifyEmail(pendingEmail, form.get('code'));
      onClose();
      showToast('Conta verificada!');
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
      showToast('Código enviado!');
    } catch (error) {
      setMessage({ text: error.message, error: true });
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Autenticação">
        <div className="modal-header">
          <strong>Entre na sua conta</strong>
          <button type="button" className="btn-ghost" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className="tabs">
            <button type="button" className={`tab${tab === 'login' ? ' active' : ''}`} onClick={() => switchTab('login')}>Entrar</button>
            <button type="button" className={`tab${tab === 'register' ? ' active' : ''}`} onClick={() => switchTab('register')}>Criar conta</button>
            {tab === 'verify' && <button type="button" className="tab active">Verificar</button>}
          </div>

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
              <div className="form-group">
                <label htmlFor="reg-name">Nome</label>
                <input id="reg-name" name="name" required />
              </div>
              <div className="form-group">
                <label htmlFor="reg-email">Email</label>
                <input id="reg-email" name="email" type="email" required />
              </div>
              <div className="form-group">
                <label htmlFor="reg-password">Senha</label>
                <input id="reg-password" name="password" type="password" required minLength={6} />
              </div>
              <div className="form-group">
                <label htmlFor="reg-confirm">Confirmar senha</label>
                <input id="reg-confirm" name="password_confirm" type="password" required />
              </div>
              <button type="submit" className="btn btn-primary btn-full">Criar conta</button>
            </form>
          )}

          {tab === 'verify' && (
            <form onSubmit={handleVerify}>
              <p style={{ marginBottom: '1rem', fontSize: '0.9rem', color: 'rgba(0,0,0,.55)' }}>
                Digite o código enviado para {pendingEmail}
              </p>
              <div className="form-group">
                <label htmlFor="verify-code">Código</label>
                <input id="verify-code" name="code" required />
              </div>
              <button type="submit" className="btn btn-primary btn-full">Verificar</button>
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

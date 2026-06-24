import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

export default function PainelLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    painelApi('/painel/session')
      .then((data) => {
        if (data.authenticated) navigate('/painel/vendedores/', { replace: true });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await painelApi('/painel/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      navigate('/painel/vendedores/', { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div className="painel-login"><p>Carregando...</p></div>;

  return (
    <div className="painel-login">
      <form className="painel-login-card" onSubmit={submit}>
        <h1>Painel Galelugi</h1>
        <p>Acesso administrativo — aprovar vendedores e operar a loja</p>
        <input
          type="text"
          placeholder="E-mail ou usuário (ex.: admin)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          required
        />
        <input
          type="password"
          placeholder="Senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
        {error && <p className="painel-error">{error}</p>}
        <button type="submit" className="btn btn-accent btn-full">Entrar</button>
        <p className="form-hint" style={{ marginTop: '0.75rem', fontSize: '0.82rem' }}>
          Conta padrão: <strong>admin</strong> · senha <strong>admin</strong>
        </p>
      </form>
    </div>
  );
}

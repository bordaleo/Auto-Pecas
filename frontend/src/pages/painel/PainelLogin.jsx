import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { painelApi } from '../../api/client';

export default function PainelLogin() {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    painelApi('/painel/session')
      .then((data) => {
        if (data.authenticated) navigate('/painel/visao/', { replace: true });
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
        body: JSON.stringify({ password }),
      });
      navigate('/painel/visao/', { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div className="painel-login"><p>Carregando...</p></div>;

  return (
    <div className="painel-login">
      <form className="painel-login-card" onSubmit={submit}>
        <h1>Painel Galelugi</h1>
        <p>Acesso operacional da loja</p>
        <input
          type="password"
          placeholder="Senha do painel"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="painel-error">{error}</p>}
        <button type="submit" className="btn btn-accent btn-full">Entrar</button>
      </form>
    </div>
  );
}

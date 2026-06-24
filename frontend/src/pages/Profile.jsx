import { useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { api, getToken } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import PageSeo from '../components/PageSeo';

export default function Profile() {
  const { user, logout, refresh } = useAuth();
  const { showToast } = useToast();
  const { openAuth, accountEmbedded } = useOutletContext() || {};
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '', phone: '', shipping_zip: '', shipping_address: '', shipping_city: '', shipping_state: '',
  });

  useEffect(() => {
    if (user) {
      setForm({
        name: user.name || '',
        phone: user.phone || '',
        shipping_zip: user.shipping_zip || '',
        shipping_address: user.shipping_address || '',
        shipping_city: user.shipping_city || '',
        shipping_state: user.shipping_state || '',
      });
    }
  }, [user]);

  if (!getToken()) {
    if (accountEmbedded) return null;
    return (
      <div className="wrap internal-page">
        <div className="internal-page-card">
          <p className="state-empty">
            <button type="button" className="btn btn-accent" onClick={() => openAuth('login')}>Entrar</button>
          </p>
        </div>
      </div>
    );
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      await api('/auth/profile', {
        method: 'PUT',
        body: JSON.stringify(form),
      });
      await refresh();
      showToast('Perfil salvo!');
    } catch (error) {
      showToast(error.message);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const formContent = (
    <form className={`${accountEmbedded ? 'form-card' : 'internal-page-card profile-form'}`} onSubmit={handleSubmit}>
      {!accountEmbedded && <h2>Dados pessoais</h2>}
      {accountEmbedded && (
        <header className="form-card-head">
          <h2>Dados pessoais</h2>
          <p className="form-hint">Usados no checkout e no cálculo de frete.</p>
        </header>
      )}
      <div className={accountEmbedded ? 'form-card-body' : undefined}>
      <div className="form-row form-row--2">
            <div className="form-group">
              <label>Nome</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Telefone</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
          </div>
          <div className="form-group">
            <label>Email</label>
            <input value={user?.email || ''} disabled />
          </div>

          <h2 className="form-section-title">Endereço padrão</h2>
          <p className="form-hint">Salvo para pré-preencher checkout e calcular frete no carrinho.</p>
          <div className="form-row form-row--2">
            <div className="form-group">
              <label>CEP</label>
              <input value={form.shipping_zip} onChange={(e) => setForm({ ...form, shipping_zip: e.target.value })} placeholder="00000-000" />
            </div>
            <div className="form-group">
              <label>UF</label>
              <input value={form.shipping_state} onChange={(e) => setForm({ ...form, shipping_state: e.target.value.toUpperCase() })} maxLength={2} />
            </div>
          </div>
          <div className="form-group">
            <label>Endereço</label>
            <input value={form.shipping_address} onChange={(e) => setForm({ ...form, shipping_address: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Cidade</label>
            <input value={form.shipping_city} onChange={(e) => setForm({ ...form, shipping_city: e.target.value })} />
          </div>

          <div className="profile-actions">
            <button type="submit" className="btn btn-accent">Salvar alterações</button>
            <button type="button" className="btn btn-secondary" onClick={handleLogout}>Sair da conta</button>
            {!accountEmbedded && <Link to="/conta/pedidos/" className="btn btn-secondary">Meus pedidos</Link>}
            {user?.is_staff && <Link to="/gerenciar/" className="btn btn-secondary">Gerenciar peças</Link>}
          </div>
      </div>
    </form>
  );

  if (accountEmbedded) return formContent;

  return (
    <>
      <PageSeo title="Minha conta | Galelugi Peças" description="Gerencie seus dados e endereço de entrega na Galelugi." />
      <div className="wrap internal-page profile-page">
        <header className="internal-page-head">
          <h1>Minha conta</h1>
          <p>Dados usados no checkout e cálculo de frete.</p>
        </header>
        {formContent}
      </div>
    </>
  );
}

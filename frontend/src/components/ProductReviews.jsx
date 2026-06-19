import { useEffect, useState } from 'react';
import { api, getToken } from '../api/client';
import { useToast } from '../context/ToastContext';

function Stars({ value, size = 'md', interactive = false, onChange }) {
  return (
    <span className={`review-stars review-stars--${size}${interactive ? ' interactive' : ''}`} aria-label={`${value} de 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type={interactive ? 'button' : undefined}
          className={n <= value ? 'star on' : 'star'}
          onClick={interactive ? () => onChange?.(n) : undefined}
          disabled={!interactive}
          aria-label={interactive ? `${n} estrelas` : undefined}
        >
          ★
        </button>
      ))}
    </span>
  );
}

function RatingBars({ reviews }) {
  const counts = [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: reviews.filter((r) => r.rating === star).length,
  }));
  const total = reviews.length || 1;

  return (
    <div className="review-bars">
      {counts.map(({ star, count }) => (
        <div key={star} className="review-bar-row">
          <span>{star}★</span>
          <div className="review-bar-track">
            <div className="review-bar-fill" style={{ width: `${(count / total) * 100}%` }} />
          </div>
          <span>{count}</span>
        </div>
      ))}
    </div>
  );
}

export default function ProductReviews({ productId }) {
  const { showToast } = useToast();
  const [data, setData] = useState({ reviews: [], average_rating: 0, review_count: 0 });
  const [form, setForm] = useState({ rating: 5, title: '', comment: '' });
  const [loading, setLoading] = useState(true);

  const load = () => {
    api(`/products/${productId}/reviews/`)
      .then(setData)
      .catch(() => setData({ reviews: [], average_rating: 0, review_count: 0 }))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [productId]);

  const submit = async (e) => {
    e.preventDefault();
    if (!getToken()) {
      showToast('Faça login para avaliar');
      return;
    }
    if (!form.comment.trim()) {
      showToast('Conte um pouco sobre a peça ou a entrega');
      return;
    }
    try {
      await api('/reviews/', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId, ...form }),
      });
      showToast('Avaliação publicada!');
      setForm({ rating: 5, title: '', comment: '' });
      load();
    } catch (err) {
      showToast(err.message);
    }
  };

  if (loading) return null;

  const avg = Number(data.average_rating) || 0;

  return (
    <section className="product-reviews internal-page-card">
      <div className="review-layout">
        <aside className="review-sidebar">
          <h2>Avaliações dos compradores</h2>
          <div className="review-score-card">
            <strong className="review-score">{avg ? avg.toFixed(1) : '—'}</strong>
            <Stars value={Math.round(avg)} />
            <span className="review-count-label">{data.review_count} avaliação(ões)</span>
          </div>
          {(data.reviews || []).length > 0 && <RatingBars reviews={data.reviews} />}
        </aside>

        <div className="review-main">
          {getToken() ? (
            <form className="review-form-card" onSubmit={submit}>
              <h3>Deixe sua avaliação</h3>
              <p className="form-hint">Comprou esta peça? Sua opinião ajuda outros mecânicos e compradores.</p>
              <div className="review-form-stars">
                <span>Sua nota</span>
                <Stars value={form.rating} size="lg" interactive onChange={(n) => setForm({ ...form, rating: n })} />
              </div>
              <input
                className="review-input"
                placeholder="Título (opcional) — ex.: Peça original, veio rápido"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
              <textarea
                className="review-textarea"
                rows={4}
                placeholder="Conte sua experiência: compatibilidade, qualidade, embalagem..."
                value={form.comment}
                onChange={(e) => setForm({ ...form, comment: e.target.value })}
                required
              />
              <button type="submit" className="btn btn-accent">Publicar avaliação</button>
            </form>
          ) : (
            <div className="review-login-hint">
              <p>Faça login para avaliar esta peça após a compra.</p>
            </div>
          )}

          <div className="review-list">
            {(data.reviews || []).length === 0 ? (
              <p className="state-empty">Nenhuma avaliação ainda. Seja o primeiro a opinar!</p>
            ) : (
              data.reviews.map((r) => (
                <article key={r.id} className="review-card">
                  <div className="review-card-head">
                    <div className="review-avatar" aria-hidden>{(r.user_name || '?')[0].toUpperCase()}</div>
                    <div>
                      <div className="review-card-meta">
                        <strong>{r.user_name}</strong>
                        {r.is_verified_purchase && <span className="tag tag--verified">Compra verificada</span>}
                      </div>
                      <Stars value={r.rating} size="sm" />
                    </div>
                    <time>{new Date(r.created_at).toLocaleDateString('pt-BR')}</time>
                  </div>
                  {r.title && <h4 className="review-card-title">{r.title}</h4>}
                  {r.comment && <p className="review-card-body">{r.comment}</p>}
                </article>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

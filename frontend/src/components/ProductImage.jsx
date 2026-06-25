import { useState } from 'react';
import { Package } from 'lucide-react';
import { resolveMediaUrl } from '../api/client';

const CATEGORY_TONES = {
  freios: '#E8621A',
  motor: '#2563EB',
  suspensao: '#059669',
  eletrica: '#D97706',
  carroceria: '#64748B',
  transmissao: '#7C3AED',
  default: '#94A3B8',
};

function toneFromUrl(url, categorySlug) {
  if (categorySlug && CATEGORY_TONES[categorySlug]) return CATEGORY_TONES[categorySlug];
  const lower = (url || '').toLowerCase();
  for (const [key, color] of Object.entries(CATEGORY_TONES)) {
    if (key !== 'default' && lower.includes(key)) return color;
  }
  return CATEGORY_TONES.default;
}

export default function ProductImage({
  src,
  alt = '',
  categorySlug = '',
  className = '',
  size = 'card',
}) {
  const [failed, setFailed] = useState(false);
  const resolved = resolveMediaUrl(src);
  const showFallback = !resolved || failed;
  const tone = toneFromUrl(resolved || categorySlug, categorySlug);

  if (showFallback) {
    return (
      <div
        className={`product-image product-image--fallback product-image--${size} ${className}`.trim()}
        style={{ '--product-image-tone': tone }}
        role="img"
        aria-label={alt || 'Peça automotiva'}
      >
        <Package size={size === 'card' ? 40 : 56} strokeWidth={1.25} aria-hidden="true" />
      </div>
    );
  }

  const isPhoto = /\.(jpe?g|png|webp|gif)(\?|$)/i.test(resolved);

  return (
    <img
      src={resolved}
      alt={alt}
      loading="lazy"
      decoding="async"
      className={`product-image product-image--${size} ${isPhoto ? 'product-image--photo' : 'product-image--icon'} ${className}`.trim()}
      onError={() => setFailed(true)}
    />
  );
}

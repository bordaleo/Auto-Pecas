export default function ProductGridSkeleton({ count = 8, catalog = false }) {
  return (
    <div
      className={`product-grid${catalog ? ' product-grid--catalog' : ''} product-grid--skeleton`}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Carregando peças"
    >
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={`product-skeleton${catalog ? ' product-skeleton--catalog' : ''}`}>
          <div className="product-skeleton__media" />
          <div className="product-skeleton__body">
            <div className="product-skeleton__line product-skeleton__line--sm" />
            <div className="product-skeleton__line" />
            <div className="product-skeleton__line product-skeleton__line--md" />
            <div className="product-skeleton__line product-skeleton__line--price" />
          </div>
        </div>
      ))}
    </div>
  );
}

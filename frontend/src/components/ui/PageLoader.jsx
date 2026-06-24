export default function PageLoader({ label = 'Carregando...' }) {
  return (
    <div className="page-loader" role="status" aria-live="polite" aria-busy="true">
      <div className="page-loader-card">
        <div className="page-loader-spinner" aria-hidden="true" />
        <p>{label}</p>
      </div>
    </div>
  );
}

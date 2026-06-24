export default function InternalPage({ title, subtitle, children }) {
  return (
    <div className="internal-page wrap">
      <header className="internal-page-head">
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </header>
      <div className="internal-page-card internal-page-body">
        {children}
      </div>
    </div>
  );
}

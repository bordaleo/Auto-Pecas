export default function FormCard({ title, hint, children, footer, className = '' }) {
  return (
    <section className={`form-card ${className}`.trim()}>
      {(title || hint) && (
        <header className="form-card-head">
          {title && <h2>{title}</h2>}
          {hint && <p className="form-hint">{hint}</p>}
        </header>
      )}
      <div className="form-card-body">{children}</div>
      {footer && <footer className="form-card-foot">{footer}</footer>}
    </section>
  );
}

export function FormSection({ title, hint, children }) {
  return (
    <div className="form-section">
      {title && <h3 className="form-section-title">{title}</h3>}
      {hint && <p className="form-hint">{hint}</p>}
      {children}
    </div>
  );
}

export function FormRow({ cols = 2, children }) {
  return <div className={`form-row form-row--${cols}`}>{children}</div>;
}

export function FormField({ label, hint, htmlFor, children, className = '' }) {
  return (
    <div className={`form-group ${className}`.trim()}>
      {label && <label htmlFor={htmlFor}>{label}</label>}
      {children}
      {hint && <small className="form-hint">{hint}</small>}
    </div>
  );
}

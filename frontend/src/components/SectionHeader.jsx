import { Link } from 'react-router-dom';

export default function SectionHeader({ title, subtitle, href, linkLabel = 'Ver mais' }) {
  return (
    <div className="section-head">
      <div>
        <h2 className="section-title">{title}</h2>
        {subtitle && <p className="section-subtitle">{subtitle}</p>}
      </div>
      {href && (
        <Link to={href} className="section-link">
          {linkLabel}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </Link>
      )}
    </div>
  );
}

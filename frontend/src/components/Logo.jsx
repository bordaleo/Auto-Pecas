export default function Logo({ compact = false, light = false }) {
  return (
    <span className={`gl-logo${compact ? ' gl-logo--compact' : ''}${light ? ' gl-logo--light' : ''}`}>
      <svg className="gl-logo-mark" viewBox="0 0 52 52" width="52" height="52" fill="none" aria-hidden="true">
        <rect width="52" height="52" rx="12" fill="url(#gl-grad)" />
        <circle cx="26" cy="26" r="14" stroke="#D4622A" strokeWidth="2.2" strokeDasharray="6 4" opacity="0.85" />
        <path
          d="M18 34c0-7.5 3.6-13 8-13s8 5.5 8 13"
          stroke="#3D8B7A"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path d="M22 26h14l-5-7 5-7H22" fill="#fff" />
        <defs>
          <linearGradient id="gl-grad" x1="0" y1="0" x2="52" y2="52">
            <stop stopColor="#0F1C2E" />
            <stop offset="1" stopColor="#1A3050" />
          </linearGradient>
        </defs>
      </svg>
      {!compact && (
        <span className="gl-logo-type">
          <span className="gl-logo-word">Galelugi</span>
          <span className="gl-logo-sub">Peças Automotivas</span>
        </span>
      )}
    </span>
  );
}

export default function SubTabs({ tabs, active, onChange }) {
  return (
    <div className="sub-tabs" role="tablist">
      {tabs.map(([key, label, badge]) => (
        <button
          key={key}
          type="button"
          role="tab"
          aria-selected={active === key}
          className={`sub-tab${active === key ? ' active' : ''}`}
          onClick={() => onChange(key)}
        >
          {label}
          {badge > 0 && <em className="sub-tab-badge">{badge}</em>}
        </button>
      ))}
    </div>
  );
}

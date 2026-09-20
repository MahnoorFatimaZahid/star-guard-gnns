const ICONS = {
  home: (
    <svg viewBox="0 0 22 22" style={{ width: 19, height: 19 }}>
      <rect x="3" y="3" width="7" height="7" rx="2" fill="currentColor" />
      <rect x="12" y="3" width="7" height="7" rx="2" fill="currentColor" opacity="0.45" />
      <rect x="3" y="12" width="7" height="7" rx="2" fill="currentColor" opacity="0.45" />
      <rect x="12" y="12" width="7" height="7" rx="2" fill="currentColor" opacity="0.45" />
    </svg>
  ),
  users: (
    <svg viewBox="0 0 22 22" style={{ width: 19, height: 19 }}>
      <circle cx="11" cy="7" r="4" fill="currentColor" />
      <path d="M3 20c0-4.4 3.6-7 8-7s8 2.6 8 7z" fill="currentColor" opacity="0.5" />
    </svg>
  ),
  repos: (
    <svg viewBox="0 0 22 22" style={{ width: 19, height: 19 }}>
      <path d="M4 4h10l4 4v10H4z" fill="currentColor" opacity="0.5" />
      <path d="M4 4h10l4 4H4z" fill="currentColor" />
    </svg>
  ),
  graph: (
    <svg viewBox="0 0 22 22" style={{ width: 19, height: 19 }}>
      <g stroke="currentColor" strokeWidth="1.6">
        <line x1="11" y1="6" x2="5" y2="16" />
        <line x1="11" y1="6" x2="17" y2="16" />
        <line x1="5" y1="16" x2="17" y2="16" />
      </g>
      <circle cx="11" cy="6" r="3" fill="currentColor" />
      <circle cx="5" cy="16" r="2.6" fill="currentColor" />
      <circle cx="17" cy="16" r="2.6" fill="currentColor" />
    </svg>
  ),
  stats: (
    <svg viewBox="0 0 22 22" style={{ width: 19, height: 19 }}>
      <rect x="4" y="11" width="3.4" height="8" rx="1.4" fill="currentColor" />
      <rect x="9.3" y="6" width="3.4" height="13" rx="1.4" fill="currentColor" />
      <rect x="14.6" y="9" width="3.4" height="10" rx="1.4" fill="currentColor" opacity="0.5" />
    </svg>
  ),
  real: (
    <svg viewBox="0 0 22 22" style={{ width: 19, height: 19 }}>
      <circle cx="11" cy="11" r="7.4" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <ellipse cx="11" cy="11" rx="3.2" ry="7.4" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
      <line x1="3.6" y1="11" x2="18.4" y2="11" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
    </svg>
  )
};

const LABELS = {
  home: 'Overview',
  users: 'Suspicious users',
  repos: 'Suspicious repos',
  graph: 'Graph view',
  stats: 'Analytics',
  real: 'Live GitHub scan'
};

export default function Rail({ page, onNavigate }) {
  return (
    <div
      style={{
        width: 72,
        flex: 'none',
        background: 'var(--surface-2)',
        borderRight: '1px solid var(--line-soft)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '22px 0',
        gap: 26
      }}
    >
      <svg viewBox="0 0 40 40" style={{ width: 30, height: 30 }} aria-label="StarGuard">
        <g stroke="#2A2C33" strokeWidth="2.5">
          <line x1="20" y1="11" x2="10" y2="29" />
          <line x1="20" y1="11" x2="30" y2="29" />
          <line x1="10" y1="29" x2="30" y2="29" />
        </g>
        <circle cx="20" cy="11" r="6" fill="var(--accent)" />
        <circle cx="10" cy="29" r="5" fill="var(--pink)" />
        <circle cx="30" cy="29" r="5" fill="var(--pink)" />
      </svg>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'center' }}>
        {Object.keys(ICONS).map((key) => {
          const on = page === key;
          return (
            <button
              key={key}
              type="button"
              className="rail-btn"
              onClick={() => onNavigate(key)}
              aria-label={LABELS[key]}
              aria-current={on ? 'page' : undefined}
              style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: on ? '#17251F' : 'transparent',
                color: on ? 'var(--accent)' : 'var(--ink-dim)'
              }}
            >
              {ICONS[key]}
            </button>
          );
        })}
      </nav>

      <div
        style={{
          marginTop: 'auto',
          width: 34,
          height: 34,
          borderRadius: '50%',
          background: '#1A1C21',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 13,
          fontWeight: 600,
          color: 'var(--ink-dim)'
        }}
      >
        SR
      </div>
    </div>
  );
}

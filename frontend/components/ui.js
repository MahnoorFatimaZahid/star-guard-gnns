export const card = {
  background: 'var(--surface)',
  border: '1px solid var(--line)',
  borderRadius: 24,
  padding: '26px 28px',
  minWidth: 0
};

export const cardTitle = { fontSize: 17, fontWeight: 600, color: 'var(--ink)', margin: 0 };

export const cardSub = { fontSize: 13, color: 'var(--ink-faint)', margin: '5px 0 0' };

export const microLabel = {
  fontSize: 11,
  letterSpacing: '0.1em',
  color: 'var(--ink-dim)',
  margin: 0
};

export const chip = {
  fontSize: 12,
  fontWeight: 500,
  color: 'var(--ink-dim)',
  background: 'var(--line-soft)',
  borderRadius: 999,
  padding: '4px 10px',
  whiteSpace: 'nowrap'
};

export const grid = (min) => ({
  display: 'grid',
  gridTemplateColumns: `repeat(auto-fit,minmax(${min}px,1fr))`,
  gap: 16
});

export function Bar({ label, value, width, color, thick = 8 }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7 }}>
        <p style={{ fontSize: 14, color: 'var(--ink)', margin: 0 }}>{label}</p>
        <p className="mono" style={{ fontSize: 13, color: 'var(--ink-faint)', margin: 0 }}>
          {value}
        </p>
      </div>
      <div
        style={{
          height: thick,
          background: 'var(--line-soft)',
          borderRadius: 999,
          overflow: 'hidden'
        }}
      >
        <div style={{ width, height: '100%', background: color }} />
      </div>
    </div>
  );
}

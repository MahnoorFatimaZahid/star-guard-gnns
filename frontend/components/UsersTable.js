'use client';

import { useCallback, useState } from 'react';
import { api } from '../lib/api';
import { useApi, LoadingBlock, ErrorBlock } from '../lib/useApi';
import { RISK } from '../lib/data';
import { chip, microLabel } from './ui';

const TRACKS =
  'minmax(0,2.2fr) minmax(0,1fr) minmax(0,1.6fr) minmax(0,0.6fr) minmax(0,0.6fr) 28px';

export default function UsersTable() {
  const [open, setOpen] = useState(null);
  const [levelFilter, setLevelFilter] = useState('all');

  const fetcher = useCallback(
    () => api.getUsers({ limit: 50, sort: 'score', level: levelFilter }),
    [levelFilter]
  );
  const { data, loading, error } = useApi(fetcher, [levelFilter]);

  if (loading) return <LoadingBlock label="Loading suspicious users…" />;
  if (error) return <ErrorBlock message={error} />;

  const USERS = data?.users || [];
  const counts = data?.level_counts || {};
  const total = data?.total || 0;

  const FILTERS = [
    { key: 'all', label: `All ${total}` },
    { key: 'critical', label: `Critical ${counts.critical || 0}` },
    { key: 'high', label: `High ${counts.high || 0}` },
    { key: 'watch', label: `Watch ${counts.watch || 0}` },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr)', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        {FILTERS.map((f) => {
          const on = levelFilter === f.key;
          return (
            <button
              key={f.key}
              type="button"
              onClick={() => setLevelFilter(f.key)}
              style={
                on
                  ? {
                      fontSize: 13,
                      fontWeight: 600,
                      color: 'var(--accent-ink)',
                      background: 'var(--accent)',
                      borderRadius: 999,
                      padding: '8px 16px',
                      border: 'none',
                      cursor: 'pointer',
                      fontFamily: 'inherit'
                    }
                  : {
                      fontSize: 13,
                      fontWeight: 500,
                      color: 'var(--ink-dim)',
                      background: 'var(--surface)',
                      border: '1px solid var(--line)',
                      borderRadius: 999,
                      padding: '8px 16px',
                      cursor: 'pointer',
                      fontFamily: 'inherit'
                    }
              }
            >
              {f.label}
            </button>
          );
        })}
        <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--ink-faint)' }}>
          Sorted by risk score
        </span>
      </div>

      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--line)',
          borderRadius: 24,
          padding: 10,
          minWidth: 0
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: TRACKS,
            gap: 12,
            padding: '14px 20px 12px'
          }}
        >
          <p className="mono" style={microLabel}>ACCOUNT</p>
          <p className="mono" style={microLabel}>RISK</p>
          <p className="mono" style={microLabel}>SIGNALS</p>
          <p className="mono" style={{ ...microLabel, textAlign: 'right' }}>AGE</p>
          <p className="mono" style={{ ...microLabel, textAlign: 'right' }}>LINKS</p>
          <p style={{ margin: 0 }} />
        </div>

        {USERS.map((u) => {
          const colour = RISK[u.level] || '#8AB4F8';
          const isOpen = open === u.id;

          return (
            <div key={u.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
              <button
                type="button"
                className="row-btn"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : u.id)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: TRACKS,
                  gap: 12,
                  alignItems: 'center',
                  width: '100%',
                  textAlign: 'left',
                  background: 'none',
                  border: 'none',
                  padding: '16px 20px',
                  cursor: 'pointer',
                  fontFamily: 'inherit'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 13, minWidth: 0 }}>
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: '50%',
                      flex: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 13,
                      fontWeight: 700,
                      background: colour,
                      color: '#0C0C0F'
                    }}
                  >
                    {u.initials}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <p
                      style={{
                        fontSize: 15,
                        fontWeight: 600,
                        color: 'var(--ink)',
                        margin: 0,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {u.handle}
                    </p>
                    <p className="mono" style={{ fontSize: 12, color: 'var(--ink-faint)', margin: '3px 0 0' }}>
                      {u.meta}
                    </p>
                  </div>
                </div>

                <div>
                  <p style={{ fontSize: 17, fontWeight: 700, margin: 0, color: colour }}>{u.score}</p>
                  <div
                    style={{
                      height: 5,
                      background: 'var(--line-soft)',
                      borderRadius: 999,
                      overflow: 'hidden',
                      marginTop: 6
                    }}
                  >
                    <div style={{ height: '100%', borderRadius: 999, width: `${u.score}%`, background: colour }} />
                  </div>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {u.tags.map((t) => (
                    <span key={t} style={chip}>{t}</span>
                  ))}
                </div>

                <p className="mono" style={{ fontSize: 13, color: 'var(--ink-dim)', margin: 0, textAlign: 'right' }}>
                  {u.age}
                </p>
                <p className="mono" style={{ fontSize: 13, color: 'var(--ink-dim)', margin: 0, textAlign: 'right' }}>
                  {u.links}
                </p>
                <p style={{ fontSize: 15, color: 'var(--ink-dim)', margin: 0, textAlign: 'center' }}>
                  {isOpen ? '−' : '+'}
                </p>
              </button>

              {isOpen && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))',
                    gap: 16,
                    padding: '4px 20px 24px'
                  }}
                >
                  <Panel label="WHY FLAGGED">
                    <p style={{ fontSize: 14, lineHeight: 1.55, color: '#C6CCD6', margin: 0 }}>{u.why}</p>
                  </Panel>

                  <Panel label="SCORE BREAKDOWN">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
                      {u.factors.map((f) => (
                        <div key={f.label}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                            <p style={{ fontSize: 13, color: '#C6CCD6', margin: 0 }}>{f.label}</p>
                            <p className="mono" style={{ fontSize: 12, color: 'var(--ink-faint)', margin: 0 }}>
                              {f.val}
                            </p>
                          </div>
                          <div
                            style={{
                              height: 6,
                              background: 'var(--line-soft)',
                              borderRadius: 999,
                              overflow: 'hidden'
                            }}
                          >
                            <div style={{ height: '100%', borderRadius: 999, width: f.w, background: f.c }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </Panel>

                  <Panel label="ACCOUNT">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <p style={{ fontSize: 13, color: '#C6CCD6', margin: 0 }}>
                        Age <span className="mono" style={{ color: 'var(--ink-faint)' }}>{u.age}</span>
                      </p>
                      <p style={{ fontSize: 13, color: '#C6CCD6', margin: 0 }}>
                        Graph links <span className="mono" style={{ color: 'var(--ink-faint)' }}>{u.links}</span>
                      </p>
                      <p style={{ fontSize: 13, color: '#C6CCD6', margin: 0 }}>
                        Risk level <span className="mono" style={{ color: colour }}>{u.level}</span>
                      </p>
                    </div>
                  </Panel>

                  <Panel label="CLUSTER NEIGHBOURS" stretch>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {u.peers.map((p) => (
                        <span
                          key={p}
                          className="mono"
                          style={{
                            fontSize: 12,
                            color: '#C6CCD6',
                            background: 'var(--line-soft)',
                            borderRadius: 999,
                            padding: '5px 11px'
                          }}
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: 9, marginTop: 'auto', paddingTop: 18 }}>
                      <button
                        type="button"
                        className="primary-btn"
                        style={{
                          flex: 1,
                          background: 'var(--accent)',
                          border: 'none',
                          borderRadius: 999,
                          padding: 10,
                          fontFamily: 'inherit',
                          fontSize: 13,
                          fontWeight: 600,
                          color: 'var(--accent-ink)',
                          cursor: 'pointer'
                        }}
                      >
                        Confirm fake
                      </button>
                      <button
                        type="button"
                        className="outline-btn"
                        style={{
                          flex: 1,
                          background: 'none',
                          border: '1px solid #2A2C33',
                          borderRadius: 999,
                          padding: 10,
                          fontFamily: 'inherit',
                          fontSize: 13,
                          fontWeight: 600,
                          color: 'var(--ink-dim)',
                          cursor: 'pointer'
                        }}
                      >
                        Dismiss
                      </button>
                    </div>
                  </Panel>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Panel({ label, children, stretch }) {
  return (
    <div
      style={{
        background: 'var(--surface-2)',
        border: '1px solid var(--line-soft)',
        borderRadius: 18,
        padding: '20px 22px',
        ...(stretch ? { display: 'flex', flexDirection: 'column' } : null)
      }}
    >
      <p className="mono" style={{ ...microLabel, margin: '0 0 14px' }}>
        {label}
      </p>
      {children}
    </div>
  );
}

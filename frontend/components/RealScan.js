'use client';
import { Fragment, useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { card, cardTitle, cardSub, chip, grid } from './ui';

// Bands for the rule-based score only. The GNN column is deliberately NOT
// banded — it is an uncalibrated raw sigmoid, and putting it on the
// dashboard's 40/60/80 scale would imply a comparability that isn't there.
function band(score) {
  if (score >= 60) return { label: 'High', color: '#F5C8D0', ink: '#3D1620' };
  if (score >= 40) return { label: 'Watch', color: '#F8DCA8', ink: '#3A2A08' };
  if (score >= 20) return { label: 'Low', color: '#C9D8F7', ink: '#17244A' };
  return { label: 'Clean', color: '#B8E6D0', ink: '#06251A' };
}

const th = {
  textAlign: 'left',
  fontSize: 11,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'var(--ink-faint)',
  fontWeight: 600,
  padding: '0 12px 10px 0',
  whiteSpace: 'nowrap'
};

const td = {
  padding: '12px 12px 12px 0',
  fontSize: 13,
  color: 'var(--ink)',
  borderTop: '1px solid var(--line-soft)',
  verticalAlign: 'top'
};

export default function RealScan({ scanState, onStartScan }) {
  const { running, error, scanId } = scanState;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cfg, setCfg] = useState(null);
  const [expanded, setExpanded] = useState(null);

  const load = useCallback(() => {
    Promise.all([api.getRealScanLatest(), api.getRealScanConfig()])
      .then(([latest, config]) => {
        setData(latest);
        setCfg(config);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Refresh once a scan finishes.
  useEffect(() => {
    if (!running && scanId) load();
  }, [running, scanId, load]);

  const results = data?.results || [];
  const neverRun = data?.never_run;
  const tokenMissing = cfg && !cfg.token_configured;
  const repos = data?.repos_checked || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* The honesty panel — the reason this is a separate tab. */}
      <div style={{ ...card, borderColor: '#3A3421', background: 'rgba(248,220,168,0.05)' }}>
        <h3 style={{ ...cardTitle, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span>This tab does not train the model</span>
          <span style={{ ...chip, background: '#F8DCA8', color: '#3A2A08', fontWeight: 600 }}>
            inference only
          </span>
        </h3>
        <p style={{ ...cardSub, lineHeight: 1.6, maxWidth: 760 }}>
          Real GitHub accounts carry no fraud labels, so there is nothing to
          compute a training loss against. This runs a forward pass using the
          weights already learned from the synthetic graph — a transfer check,
          not an evaluation. There is no precision or recall figure here,
          because any such figure would be invented.
        </p>
        <p style={{ ...cardSub, lineHeight: 1.6, maxWidth: 760, marginTop: 10 }}>
          <strong style={{ color: 'var(--ink)' }}>Trust the rule-based score.</strong>{' '}
          It is a transparent 0&ndash;100 threshold check with a stated reason for
          every point. The GNN column is a raw, uncalibrated sigmoid and is not
          on the same scale as the rest of this dashboard.
        </p>
      </div>

      {tokenMissing && (
        <div style={{ ...card, borderColor: '#4A2630', background: 'rgba(245,200,208,0.06)' }}>
          <h3 style={cardTitle}>A GitHub token is needed</h3>
          <p style={{ ...cardSub, lineHeight: 1.6, maxWidth: 760 }}>{cfg.token_help}</p>
        </div>
      )}

      {error && (
        <div style={{ ...card, borderColor: '#4A2630', background: 'rgba(245,200,208,0.06)' }}>
          <h3 style={cardTitle}>Scan failed</h3>
          <p style={{ ...cardSub, lineHeight: 1.6, maxWidth: 760 }}>{error}</p>
        </div>
      )}

      <div style={card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 280px', minWidth: 0 }}>
            <h3 style={cardTitle}>
              {running ? 'Scanning live GitHub…' : neverRun ? 'No scan run yet' : 'Last scan'}
            </h3>
            <p style={cardSub}>
              {running
                ? 'Reading WatchEvents, looking up profiles via GraphQL, then scoring. Network-bound — this takes a few minutes.'
                : neverRun
                ? 'Run a scan to point the trained model at real accounts.'
                : results.length +
                  ' accounts checked across ' +
                  repos.length +
                  ' repos · ' +
                  (data.profiles_enriched || 0) +
                  ' profiles enriched'}
            </p>
          </div>
          <button
            type="button"
            onClick={onStartScan}
            disabled={running || tokenMissing}
            style={{
              background: running || tokenMissing ? 'var(--line-soft)' : 'var(--accent)',
              color: running || tokenMissing ? 'var(--ink-faint)' : 'var(--accent-ink)',
              border: 'none',
              borderRadius: 999,
              padding: '11px 22px',
              fontFamily: 'inherit',
              fontSize: 14,
              fontWeight: 600,
              cursor: running || tokenMissing ? 'default' : 'pointer'
            }}
          >
            {running ? 'Scanning…' : 'Scan real GitHub'}
          </button>
        </div>

        {!running && repos.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
            {repos.map((r) => (
              <span key={r} style={chip}>
                {r}
              </span>
            ))}
          </div>
        )}
      </div>

      {!loading && results.length > 0 && (
        <>
          <div style={grid(190)}>
            {[
              ['Accounts checked', results.length],
              ['Rule score ≥ 60', results.filter((r) => r.rule_based_score >= 60).length],
              ['Rule score ≥ 40', results.filter((r) => r.rule_based_score >= 40).length],
              ['With co-star partners', results.filter((r) => r.co_star_burst_partners > 0).length]
            ].map(([label, value]) => (
              <div key={label} style={card}>
                <p style={{ ...cardSub, margin: 0 }}>{label}</p>
                <p
                  className="mono"
                  style={{ fontSize: 26, fontWeight: 700, color: 'var(--ink)', margin: '6px 0 0' }}
                >
                  {value}
                </p>
              </div>
            ))}
          </div>

          <div style={{ ...card, overflowX: 'auto' }}>
            <h3 style={cardTitle}>Every account checked</h3>
            <p style={cardSub}>Sorted by rule-based score. Click a row for the reasons behind it.</p>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 18 }}>
              <thead>
                <tr>
                  <th style={th}>Account</th>
                  <th style={th}>Rule score</th>
                  <th style={th}>GNN (uncalibrated)</th>
                  <th style={th}>Stars</th>
                  <th style={th}>Co-star partners</th>
                  <th style={th}>Followers</th>
                  <th style={th}>Age (days)</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => {
                  const b = band(r.rule_based_score);
                  const open = expanded === i;
                  return (
                    <Fragment key={r.handle}>
                      <tr onClick={() => setExpanded(open ? null : i)} style={{ cursor: 'pointer' }}>
                        <td style={td}>
                          <a
                            href={r.github_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            style={{ color: 'var(--ink)', fontWeight: 500 }}
                          >
                            {r.handle}
                          </a>
                          {!r.has_profile_data && (
                            <span style={{ ...chip, marginLeft: 8, fontSize: 11 }}>no profile</span>
                          )}
                        </td>
                        <td style={td}>
                          <span
                            style={{
                              background: b.color,
                              color: b.ink,
                              borderRadius: 999,
                              padding: '3px 10px',
                              fontSize: 12,
                              fontWeight: 600,
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {r.rule_based_score} · {b.label}
                          </span>
                        </td>
                        <td className="mono" style={{ ...td, color: 'var(--ink-faint)' }}>
                          {r.gnn_confidence_experimental === '' ? '—' : r.gnn_confidence_experimental}
                        </td>
                        <td className="mono" style={td}>
                          {r.star_count}
                        </td>
                        <td className="mono" style={td}>
                          {r.co_star_burst_partners}
                        </td>
                        <td className="mono" style={td}>
                          {r.followers === '' ? '—' : r.followers}
                        </td>
                        <td className="mono" style={td}>
                          {r.account_age_days === '' ? '—' : r.account_age_days}
                        </td>
                      </tr>
                      {open && (
                        <tr>
                          <td colSpan={7} style={{ ...td, background: 'var(--surface-2)' }}>
                            <p style={{ ...cardSub, margin: '0 0 8px', color: 'var(--ink)' }}>
                              Why it scored {r.rule_based_score}
                            </p>
                            <ul
                              style={{
                                margin: 0,
                                paddingLeft: 18,
                                color: 'var(--ink-dim)',
                                fontSize: 13,
                                lineHeight: 1.7
                              }}
                            >
                              {r.rule_based_reasons.map((reason) => (
                                <li key={reason}>{reason}</li>
                              ))}
                            </ul>
                            <p style={{ ...cardSub, margin: '14px 0 8px', color: 'var(--ink)' }}>
                              Approximated inputs
                            </p>
                            <ul
                              style={{
                                margin: 0,
                                paddingLeft: 18,
                                color: 'var(--ink-faint)',
                                fontSize: 12,
                                lineHeight: 1.7
                              }}
                            >
                              {r.approximated_fields.map((f) => (
                                <li key={f}>{f}</li>
                              ))}
                            </ul>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

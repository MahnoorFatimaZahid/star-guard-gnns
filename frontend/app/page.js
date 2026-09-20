'use client';

import { useState } from 'react';
import Rail from '../components/Rail';
import KpiRow from '../components/KpiRow';
import Overview from '../components/Overview';
import UsersTable from '../components/UsersTable';
import Repos from '../components/Repos';
import GraphView from '../components/GraphView';
import Analytics from '../components/Analytics';
import RealScan from '../components/RealScan';
import { PAGES } from '../lib/data';
import { api } from '../lib/api';

const PILLS = [
  ['home', 'Overview'],
  ['users', 'Users'],
  ['repos', 'Repos'],
  ['graph', 'Graph'],
  ['stats', 'Analytics'],
  ['real', 'Live scan']
];

export default function Page() {
  const [page, setPage] = useState('home');
  const [retraining, setRetraining] = useState(false);
  const [scan, setScan] = useState({ running: false, error: null, scanId: null });
  const [title, sub] = PAGES[page];

  // Synthetic path: regenerates the graph AND trains the GNN. Ground truth
  // is known here, which is why this one can report accuracy.
  const handleRetrain = async () => {
    if (retraining) return;
    setRetraining(true);
    try {
      const res = await api.runAnalysis({ lookback_days: 90 });
      const poll = setInterval(async () => {
        const status = await api.getAnalysisStatus(res.analysis_id);
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(poll);
          setRetraining(false);
          if (status.status === 'completed') window.location.reload();
        }
      }, 3000);
    } catch (err) {
      setRetraining(false);
      alert(`Couldn't start retraining: ${err.message}`);
    }
  };

  // Real path: forward pass only. No labels exist for live accounts, so
  // nothing is trained and no accuracy is reported.
  const handleRealScan = async () => {
    if (scan.running) return;
    setPage('real');
    setScan({ running: true, error: null, scanId: null });
    try {
      const res = await api.runRealScan({ max_profiles: 150 });
      setScan({ running: true, error: null, scanId: res.scan_id });
      const poll = setInterval(async () => {
        try {
          const status = await api.getRealScanStatus(res.scan_id);
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(poll);
            setScan({
              running: false,
              error: status.status === 'failed' ? status.error : null,
              scanId: res.scan_id
            });
          }
        } catch (err) {
          clearInterval(poll);
          setScan({ running: false, error: err.message, scanId: res.scan_id });
        }
      }, 4000);
    } catch (err) {
      setScan({ running: false, error: err.message, scanId: null });
    }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Rail page={page} onNavigate={setPage} />

      <main
        style={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          padding: '22px 26px 40px'
        }}
      >
        <div style={{ marginBottom: 18 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--ink)', margin: 0 }}>
            {title}
          </h1>
          <p style={{ fontSize: 14, color: 'var(--ink-dim)', margin: '6px 0 0' }}>{sub}</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', marginBottom: 26 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              background: 'var(--surface)',
              border: '1px solid var(--line)',
              borderRadius: 999,
              padding: 5
            }}
          >
            {PILLS.map(([key, label]) => {
              const on = page === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setPage(key)}
                  style={{
                    border: 'none',
                    borderRadius: 999,
                    padding: '9px 18px',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    fontSize: 14,
                    fontWeight: 600,
                    background: on ? 'var(--ink)' : 'transparent',
                    color: on ? '#0C0C0F' : 'var(--ink-faint)'
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 9,
              background: 'var(--surface)',
              border: '1px solid var(--line)',
              borderRadius: 999,
              padding: '10px 18px',
              flex: '1 1 180px',
              minWidth: 160,
              maxWidth: 280
            }}
          >
            <svg viewBox="0 0 20 20" style={{ width: 15, height: 15, flex: 'none' }} aria-hidden="true">
              <circle cx="8.5" cy="8.5" r="5.6" fill="none" stroke="#7A8290" strokeWidth="2" />
              <line x1="12.8" y1="12.8" x2="18" y2="18" stroke="#7A8290" strokeWidth="2" />
            </svg>
            <input
              type="text"
              placeholder="Search user or repo"
              style={{
                flex: 1,
                minWidth: 0,
                background: 'none',
                border: 'none',
                outline: 'none',
                fontFamily: 'inherit',
                fontSize: 14,
                color: 'var(--ink)'
              }}
            />
          </label>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginLeft: 'auto', flexWrap: 'wrap' }}>
            <button type="button" className="ghost-btn" style={ghost}>Export</button>

            {/* Two buttons, deliberately not symmetric: only one of them learns. */}
            <button
              type="button"
              className="ghost-btn"
              onClick={handleRealScan}
              disabled={scan.running}
              title="Forward pass only — real accounts have no labels to train against"
              style={{
                ...ghost,
                cursor: scan.running ? 'default' : 'pointer',
                opacity: scan.running ? 0.6 : 1
              }}
            >
              {scan.running ? 'Scanning real GitHub…' : 'Scan real GitHub · score only'}
            </button>

            <button
              type="button"
              className="primary-btn"
              onClick={handleRetrain}
              disabled={retraining}
              title="Regenerates the synthetic graph and retrains the GNN with backprop"
              style={{
                background: 'var(--accent)',
                border: 'none',
                borderRadius: 999,
                padding: '11px 20px',
                fontFamily: 'inherit',
                fontSize: 14,
                fontWeight: 600,
                color: 'var(--accent-ink)',
                cursor: retraining ? 'default' : 'pointer',
                opacity: retraining ? 0.6 : 1
              }}
            >
              {retraining ? 'Regenerating + retraining…' : 'Retrain on synthetic · learns'}
            </button>
          </div>
        </div>

        {/* The KPI row is computed from the synthetic DB, so it would be
            misleading above live-GitHub results. */}
        {page !== 'real' && <KpiRow />}

        {page === 'home' && <Overview />}
        {page === 'users' && <UsersTable />}
        {page === 'repos' && <Repos />}
        {page === 'graph' && <GraphView />}
        {page === 'stats' && <Analytics />}
        {page === 'real' && <RealScan scanState={scan} onStartScan={handleRealScan} />}
      </main>
    </div>
  );
}

const ghost = {
  background: 'var(--surface)',
  border: '1px solid var(--line)',
  borderRadius: 999,
  padding: '10px 18px',
  fontFamily: 'inherit',
  fontSize: 14,
  fontWeight: 500,
  color: 'var(--ink-dim)',
  cursor: 'pointer'
};

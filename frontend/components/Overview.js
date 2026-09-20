'use client';

import { useCallback } from 'react';
import { api } from '../lib/api';
import { useApi, LoadingBlock, ErrorBlock } from '../lib/useApi';
import { Bar, card, cardSub, cardTitle } from './ui';

export default function Overview() {
  const fetcher = useCallback(() => api.getStats(), []);
  const { data, loading, error } = useApi(fetcher);

  if (loading) return <LoadingBlock label="Loading overview…" />;
  if (error) return <ErrorBlock message={error} />;

  const FLAG_REASONS = data?.flag_reasons || [];
  const CLUSTERS = data?.clusters || [];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 16 }}>
      <div style={{ ...card, gridColumn: 'span 2' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 16,
            flexWrap: 'wrap'
          }}
        >
          <div>
            <p style={cardTitle}>Flagged accounts over time</p>
            <p style={cardSub}>Spikes line up with paid-star campaigns</p>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--accent-ink)',
                background: 'var(--accent)',
                borderRadius: 999,
                padding: '5px 12px'
              }}
            >
              Daily
            </span>
            <span
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: 'var(--ink-faint)',
                border: '1px solid var(--line)',
                borderRadius: 999,
                padding: '5px 12px'
              }}
            >
              Weekly
            </span>
          </div>
        </div>

        <svg viewBox="0 0 760 240" style={{ width: '100%', height: 'auto', marginTop: 18 }}>
          <defs>
            <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34D399" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#34D399" stopOpacity="0" />
            </linearGradient>
          </defs>
          <g stroke="#17181C" strokeWidth="1">
            <line x1="40" y1="40" x2="740" y2="40" />
            <line x1="40" y1="100" x2="740" y2="100" />
            <line x1="40" y1="160" x2="740" y2="160" />
            <line x1="40" y1="200" x2="740" y2="200" />
          </g>
          <path
            d="M40 186 L110 178 L180 182 L250 150 L320 158 L390 96 L460 120 L530 104 L600 58 L670 74 L740 44 L740 200 L40 200 Z"
            fill="url(#areaFill)"
          />
          <path
            d="M40 186 L110 178 L180 182 L250 150 L320 158 L390 96 L460 120 L530 104 L600 58 L670 74 L740 44"
            fill="none"
            stroke="#34D399"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="600" cy="58" r="6" fill="#34D399" stroke="#101116" strokeWidth="3" />
          <g fontFamily="var(--font-mono), monospace" fontSize="11" fill="#7A8290">
            <text x="30" y="204" textAnchor="end">0</text>
            <text x="30" y="164" textAnchor="end">40</text>
            <text x="30" y="104" textAnchor="end">80</text>
            <text x="30" y="44" textAnchor="end">120</text>
            <text x="40" y="226">Jun</text>
            <text x="180" y="226">Jul</text>
            <text x="320" y="226">Aug</text>
            <text x="460" y="226">Sep</text>
            <text x="600" y="226">Oct</text>
            <text x="740" y="226" textAnchor="end">Nov</text>
          </g>
        </svg>
      </div>

      <div style={card}>
        <p style={cardTitle}>Verdict split</p>
        <p style={cardSub}>{(data?.kpis?.[0]?.value) || ''} accounts</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 22, marginTop: 18, flexWrap: 'wrap' }}>
          <svg viewBox="0 0 120 120" style={{ width: 140, height: 140, flex: 'none' }}>
            <circle cx="60" cy="60" r="46" fill="none" stroke="#1B1D23" strokeWidth="16" />
            <circle
              cx="60"
              cy="60"
              r="46"
              fill="none"
              stroke="#B8E6D0"
              strokeWidth="16"
              strokeDasharray="253 289"
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
            />
            <circle
              cx="60"
              cy="60"
              r="46"
              fill="none"
              stroke="#F8DCA8"
              strokeWidth="16"
              strokeDasharray="25 289"
              strokeLinecap="round"
              transform="rotate(220 60 60)"
            />
            <circle
              cx="60"
              cy="60"
              r="46"
              fill="none"
              stroke="#F5C8D0"
              strokeWidth="16"
              strokeDasharray="9 289"
              strokeLinecap="round"
              transform="rotate(256 60 60)"
            />
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 120 }}>
            {[
              ['Clean', '87.6%', '#B8E6D0'],
              ['Watch', '8.6%', '#F8DCA8'],
              ['Fake', '3.8%', '#F5C8D0']
            ].map(([name, pct, colour]) => (
              <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span
                  style={{ width: 10, height: 10, borderRadius: 3, background: colour, flex: 'none' }}
                />
                <p style={{ fontSize: 14, color: 'var(--ink-dim)', margin: 0 }}>
                  {name} <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{pct}</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={card}>
        <p style={{ ...cardTitle, marginBottom: 4 }}>Why accounts got flagged</p>
        <p style={{ ...cardSub, margin: '0 0 20px' }}>Most common patterns this period</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {FLAG_REASONS.map((r) => (
            <Bar key={r.label} label={r.label} value={r.count} width={r.width} color={r.color} />
          ))}
        </div>
      </div>

      <div style={{ ...card, display: 'flex', flexDirection: 'column' }}>
        <p style={{ ...cardTitle, marginBottom: 4 }}>Biggest clusters</p>
        <p style={{ ...cardSub, margin: '0 0 18px' }}>Groups moving together</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {CLUSTERS.map((c) => (
            <div
              key={c.tag}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                background: 'var(--surface-2)',
                border: '1px solid var(--line-soft)',
                borderRadius: 16,
                padding: '14px 16px'
              }}
            >
              <div
                className="mono"
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 12,
                  background: 'var(--line-soft)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flex: 'none',
                  fontSize: 13,
                  color: 'var(--accent)'
                }}
              >
                {c.tag}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', margin: 0 }}>{c.name}</p>
                <p style={{ fontSize: 12.5, color: 'var(--ink-faint)', margin: '3px 0 0' }}>{c.detail}</p>
              </div>
              <p className="mono" style={{ fontSize: 15, color: 'var(--pink)', margin: 0, flex: 'none' }}>
                {c.size}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

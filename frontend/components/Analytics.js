'use client';

import { useCallback } from 'react';
import { api } from '../lib/api';
import { useApi, LoadingBlock, ErrorBlock } from '../lib/useApi';
import { Bar, card, cardSub, cardTitle } from './ui';

export default function Analytics() {
  const fetcher = useCallback(() => api.getAnalytics(), []);
  const { data, loading, error } = useApi(fetcher);

  if (loading) return <LoadingBlock label="Loading analytics…" />;
  if (error) return <ErrorBlock message={error} />;

  const HEATMAP = data?.heatmap || [];
  const AGE_BARS = data?.age_bars || [];
  const MODEL_SCORES = data?.model_scores || [];
  const noGraphScore = MODEL_SCORES.find((m) => m.label.toLowerCase().includes('no graph'));
  const bestScore = MODEL_SCORES[0];
  const gap =
    bestScore && noGraphScore
      ? Math.round((parseFloat(bestScore.val) - parseFloat(noGraphScore.val)) * 100)
      : null;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 16 }}>
      <div style={card}>
        <p style={{ ...cardTitle, marginBottom: 4 }}>When flagged accounts act</p>
        <p style={{ ...cardSub, margin: '0 0 20px' }}>Hour of day, UTC — bots cluster off-peak</p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12,1fr)', gap: 5 }}>
          {HEATMAP.map((colour, i) => (
            <div key={i} style={{ aspectRatio: '1', borderRadius: 5, background: colour }} />
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 16 }}>
          <p className="mono" style={{ fontSize: 11, color: 'var(--ink-dim)', margin: 0 }}>LOW</p>
          <div
            style={{
              flex: 1,
              height: 6,
              borderRadius: 999,
              background: 'linear-gradient(to right,#17181C,#1E3A2F,#2A6B52,#34D399)'
            }}
          />
          <p className="mono" style={{ fontSize: 11, color: 'var(--ink-dim)', margin: 0 }}>HIGH</p>
        </div>
      </div>

      <div style={card}>
        <p style={{ ...cardTitle, marginBottom: 4 }}>Account age at flag time</p>
        <p style={{ ...cardSub, margin: '0 0 22px' }}>Fake accounts skew very young</p>

        <svg viewBox="0 0 360 200" style={{ width: '100%', height: 'auto' }}>
          <g stroke="#17181C" strokeWidth="1">
            <line x1="0" y1="170" x2="360" y2="170" />
            <line x1="0" y1="115" x2="360" y2="115" />
            <line x1="0" y1="60" x2="360" y2="60" />
          </g>
          {AGE_BARS.map((b) => (
            <rect key={b.label} x={b.x} y={b.y} width="38" height={b.h} rx="8" fill={b.c} />
          ))}
          <g fontFamily="var(--font-mono), monospace" fontSize="10" fill="#7A8290" textAnchor="middle">
            {AGE_BARS.map((b) => (
              <text key={b.label} x={b.x + 19} y="188">
                {b.label}
              </text>
            ))}
          </g>
        </svg>
      </div>

      <div style={card}>
        <p style={{ ...cardTitle, marginBottom: 4 }}>Model vs baselines</p>
        <p style={{ ...cardSub, margin: '0 0 22px' }}>Precision on the held-out test split</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {MODEL_SCORES.map((m) => (
            <Bar key={m.label} label={m.label} value={m.val} width={m.w} color={m.c} thick={9} />
          ))}
        </div>

        <p
          style={{
            fontSize: 13,
            lineHeight: 1.5,
            color: 'var(--ink-faint)',
            margin: '20px 0 0',
            paddingTop: 18,
            borderTop: '1px solid var(--line-soft)'
          }}
        >
          {gap !== null
            ? `The no-graph baseline is the one that matters: the ${gap}-point gap is what the edges are worth.`
            : 'Comparing the trained GraphSAGE model against baselines with progressively less graph structure.'}
        </p>
      </div>
    </div>
  );
}

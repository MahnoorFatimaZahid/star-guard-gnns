'use client';

import { useCallback, useMemo, useState } from 'react';
import { api } from '../lib/api';
import { useApi, LoadingBlock, ErrorBlock } from '../lib/useApi';
import { cardSub, cardTitle, microLabel } from './ui';

const RISK_COLOR = { critical: '#F5C8D0', high: '#F8DCA8', watch: '#8AB4F8', safe: '#34D399' };
const W = 800;
const H = 430;
const CX = W / 2;
const CY = H / 2;

function layout(nodes, edges) {
  const users = nodes.filter((n) => n.type === 'user');
  const repos = nodes.filter((n) => n.type === 'repo');
  const positions = {};

  const uR = 150;
  users.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, users.length);
    positions[n.id] = {
      x: CX - 120 + uR * Math.cos(angle) * 0.75,
      y: CY + uR * Math.sin(angle) * 0.75,
    };
  });

  const rR = 90;
  repos.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, repos.length);
    positions[n.id] = {
      x: CX + 180 + rR * Math.cos(angle),
      y: CY - 60 + rR * Math.sin(angle),
    };
  });

  return positions;
}

export default function GraphView() {
  const [selected, setSelected] = useState(null);
  const [showAll, setShowAll] = useState(false);

  const fetcher = useCallback(() => api.getGraph({ limit_nodes: 50 }), []);
  const { data, loading, error } = useApi(fetcher);

  const positions = useMemo(() => {
    if (!data) return {};
    return layout(data.nodes, data.edges);
  }, [data]);

  if (loading) return <LoadingBlock label="Loading star network…" />;
  if (error) return <ErrorBlock message={error} />;

  const nodes = data?.nodes || [];
  const edges = data?.edges || [];
  const cluster = data?.focused_cluster;
  const visibleNodes = showAll ? nodes : nodes.filter((n) => n.type === 'repo' || n.risk_level !== 'safe');
  const visibleIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));

  const selectedNode = nodes.find((n) => n.id === selected);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 16 }}>
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--line)',
          borderRadius: 24,
          padding: '24px 26px',
          gridColumn: 'span 2',
          minWidth: 0
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 14,
            flexWrap: 'wrap',
            marginBottom: 8
          }}
        >
          <div>
            <p style={cardTitle}>Star network{cluster ? ` — ${cluster.name}` : ''}</p>
            <p style={cardSub}>Click a node for detail · showing largest coordinated cluster</p>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              type="button"
              onClick={() => setShowAll(false)}
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: !showAll ? 'var(--accent-ink)' : 'var(--ink-faint)',
                background: !showAll ? 'var(--accent)' : 'transparent',
                borderRadius: 999,
                padding: '5px 12px',
                border: !showAll ? 'none' : '1px solid var(--line)',
                cursor: 'pointer',
                fontFamily: 'inherit'
              }}
            >
              Suspicious only
            </button>
            <button
              type="button"
              onClick={() => setShowAll(true)}
              style={{
                fontSize: 12,
                fontWeight: showAll ? 600 : 500,
                color: showAll ? 'var(--accent-ink)' : 'var(--ink-faint)',
                background: showAll ? 'var(--accent)' : 'transparent',
                border: showAll ? 'none' : '1px solid var(--line)',
                borderRadius: 999,
                padding: '5px 12px',
                cursor: 'pointer',
                fontFamily: 'inherit'
              }}
            >
              All nodes
            </button>
          </div>
        </div>

        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
          <g stroke="#23262D" strokeWidth="1.2" opacity="0.6">
            {visibleEdges.map((e, i) => {
              const s = positions[e.source];
              const t = positions[e.target];
              if (!s || !t) return null;
              return <line key={i} x1={s.x} y1={s.y} x2={t.x} y2={t.y} />;
            })}
          </g>

          {visibleNodes.map((n) => {
            const pos = positions[n.id];
            if (!pos) return null;
            const colour = n.type === 'repo' ? '#F2F4F7' : RISK_COLOR[n.risk_level] || '#8AB4F8';
            const isSel = selected === n.id;
            return (
              <g key={n.id} onClick={() => setSelected(n.id)} style={{ cursor: 'pointer' }}>
                {n.type === 'repo' ? (
                  <rect
                    x={pos.x - 14}
                    y={pos.y - 14}
                    width="28"
                    height="28"
                    rx="8"
                    fill={colour}
                    stroke={isSel ? '#34D399' : 'none'}
                    strokeWidth="3"
                  />
                ) : (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={Math.max(6, n.size / 3)}
                    fill={colour}
                    stroke={isSel ? '#34D399' : 'none'}
                    strokeWidth="3"
                  />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--line)',
          borderRadius: 24,
          padding: '24px 26px',
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 18
        }}
      >
        <div>
          <p style={{ ...cardTitle, marginBottom: 14 }}>Legend</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
            <LegendRow colour={RISK_COLOR.critical} shape="dot" label="Critical risk user" />
            <LegendRow colour={RISK_COLOR.watch} shape="dot" label="Watch / lower risk user" />
            <LegendRow colour="#F2F4F7" shape="square" label="Repository" />
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--line-soft)', paddingTop: 18 }}>
          <p className="mono" style={{ ...microLabel, margin: '0 0 12px' }}>
            SELECTED NODE
          </p>
          {selectedNode ? (
            <>
              <p className="mono" style={{ fontSize: 15, color: 'var(--ink)', margin: 0 }}>
                {selectedNode.label}
              </p>
              <p style={{ fontSize: 13, color: 'var(--ink-faint)', margin: '6px 0 0' }}>
                {selectedNode.type === 'repo' ? 'repository' : 'user'} · risk {selectedNode.score}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 14 }}>
                <span
                  style={{
                    fontSize: 12,
                    color: 'var(--ink-dim)',
                    background: 'var(--line-soft)',
                    borderRadius: 999,
                    padding: '4px 10px'
                  }}
                >
                  {selectedNode.risk_level}
                </span>
              </div>
            </>
          ) : (
            <p style={{ fontSize: 13, color: 'var(--ink-faint)', margin: 0 }}>
              Click a node in the graph to inspect it.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function LegendRow({ colour, shape, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
      <span
        style={{
          width: shape === 'square' ? 14 : 13,
          height: 13,
          borderRadius: shape === 'square' ? 4 : '50%',
          background: colour,
          flex: 'none'
        }}
      />
      <p style={{ fontSize: 14, color: 'var(--ink-dim)', margin: 0 }}>{label}</p>
    </div>
  );
}

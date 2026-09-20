export const RISK = {
  critical: '#F5C8D0',
  high: '#F8DCA8',
  watch: '#8AB4F8'
};

export const PAGES = {
  home: ['Overview', 'Star-fraud signals across 1,204 tracked repositories'],
  users: ['Suspicious users', '312 accounts flagged — highest risk first'],
  repos: ['Suspicious repos', '47 repositories with abnormal star patterns'],
  graph: ['Graph view', 'Who starred what, and who moves together'],
  stats: ['Analytics', 'Model performance and fraud patterns'],
  real: ['Live GitHub scan', 'The trained model pointed at real accounts — scoring only, no training']
};

export const KPIS = [
  {
    label: 'Accounts scanned',
    badge: '90d',
    value: '48,912',
    bg: '#B8E6D0',
    ink: '#06251A',
    labelInk: '#123528',
    path: 'M2 32 L24 28 L46 30 L68 22 L90 25 L112 16 L134 19 L156 11 L178 14 L198 6'
  },
  {
    label: 'Flagged fake',
    badge: '+18',
    value: '312',
    bg: '#F5C8D0',
    ink: '#3D1620',
    labelInk: '#3D1620',
    path: 'M2 34 L24 30 L46 31 L68 24 L90 26 L112 14 L134 18 L156 9 L178 12 L198 4'
  },
  {
    label: 'Bot clusters',
    badge: '9',
    value: '84',
    bg: '#C9D8F7',
    ink: '#17244A',
    labelInk: '#17244A',
    note: 'accounts in the largest ring'
  },
  {
    label: 'Precision @100',
    badge: 'labelled',
    value: '0.91',
    bg: '#F8DCA8',
    ink: '#42300C',
    labelInk: '#42300C',
    note: 'recall 0.78 · AUC 0.94'
  }
];

export const FLAG_REASONS = [
  { label: 'Bulk starring', count: 184, width: '92%', color: '#34D399' },
  { label: 'Same-day creation', count: 141, width: '71%', color: '#8AB4F8' },
  { label: 'Empty profile', count: 98, width: '49%', color: '#F8DCA8' },
  { label: 'Mutual-follow ring', count: 62, width: '31%', color: '#F5C8D0' }
];

export const CLUSTERS = [
  { tag: '#4', name: 'Same-minute signups', detail: 'Created 14 Oct, 02:10–02:50 UTC', size: '84' },
  { tag: '#7', name: 'Mutual-follow ring', detail: 'Follows almost nobody outside itself', size: '61' },
  { tag: '#2', name: 'Fork farm', detail: 'Forks without a single commit', size: '38' }
];

export const USERS = [
  {
    id: 'starbot-4471',
    handle: '@starbot-4471',
    initials: 'SB',
    meta: '0 repos · 0 commits',
    score: 96,
    level: 'critical',
    tags: ['Bulk starrer', 'Bot cluster', 'Empty profile'],
    age: '11 d',
    links: 83,
    why: 'Created within the same 40-minute window as 62 other accounts, then starred 41 repositories in six hours — 38 of which were starred by the same group. No commits, no forks, no followers outside the cluster.',
    factors: [
      { label: 'Cluster membership', val: '0.94', w: '94%', c: '#F5C8D0' },
      { label: 'Star burst timing', val: '0.89', w: '89%', c: '#F5C8D0' },
      { label: 'Profile emptiness', val: '0.81', w: '81%', c: '#F8DCA8' },
      { label: 'Account age', val: '0.76', w: '76%', c: '#F8DCA8' }
    ],
    peers: ['@starbot-4472', '@gh-user-9981', '@dev00x41', '@quickstar-77', '+80 more']
  },
  {
    id: 'gh-user-9981',
    handle: '@gh-user-9981',
    initials: 'GU',
    meta: '1 repo · 2 commits',
    score: 91,
    level: 'critical',
    tags: ['Bot cluster', 'Mutual-follow ring'],
    age: '11 d',
    links: 79,
    why: 'Follows and is followed by 79 accounts from the same cluster and almost nobody outside it. Its single repository is a fork with no changes.',
    factors: [
      { label: 'Mutual-follow density', val: '0.92', w: '92%', c: '#F5C8D0' },
      { label: 'Cluster membership', val: '0.88', w: '88%', c: '#F5C8D0' },
      { label: 'Account age', val: '0.74', w: '74%', c: '#F8DCA8' }
    ],
    peers: ['@starbot-4471', '@dev00x41', '@quickstar-77', '+76 more']
  },
  {
    id: 'quickstar-77',
    handle: '@quickstar-77',
    initials: 'QS',
    meta: '0 repos · 0 commits',
    score: 88,
    level: 'critical',
    tags: ['Bulk starrer', 'Suspicious timing'],
    age: '23 d',
    links: 61,
    why: 'Starred 120 repositories across three separate bursts, each lasting under two hours and each overlapping heavily with the same cluster.',
    factors: [
      { label: 'Star burst timing', val: '0.91', w: '91%', c: '#F5C8D0' },
      { label: 'Cluster membership', val: '0.79', w: '79%', c: '#F8DCA8' },
      { label: 'Profile emptiness', val: '0.72', w: '72%', c: '#F8DCA8' }
    ],
    peers: ['@starbot-4471', '@gh-user-9981', '+58 more']
  },
  {
    id: 'dev00x41',
    handle: '@dev00x41',
    initials: 'DX',
    meta: '3 repos · 14 commits',
    score: 74,
    level: 'high',
    tags: ['Bot cluster', 'Low-effort commits'],
    age: '4 mo',
    links: 44,
    why: 'Has real commit history, but all of it lands in repositories starred by the cluster, and the commits are single-character README edits.',
    factors: [
      { label: 'Cluster membership', val: '0.77', w: '77%', c: '#F8DCA8' },
      { label: 'Commit triviality', val: '0.71', w: '71%', c: '#F8DCA8' },
      { label: 'Star burst timing', val: '0.52', w: '52%', c: '#8AB4F8' }
    ],
    peers: ['@starbot-4471', '@quickstar-77', '+41 more']
  },
  {
    id: 'mchen-builds',
    handle: '@mchen-builds',
    initials: 'MC',
    meta: '19 repos · 1.2k commits',
    score: 58,
    level: 'watch',
    tags: ['Bulk starrer'],
    age: '3 y',
    links: 12,
    why: 'A genuine long-standing account that occasionally stars 30 or more repositories in a sitting. Flagged for review, most likely a false positive.',
    factors: [
      { label: 'Star burst timing', val: '0.64', w: '64%', c: '#8AB4F8' },
      { label: 'Cluster membership', val: '0.21', w: '21%', c: '#2A2C33' },
      { label: 'Account age', val: '0.08', w: '8%', c: '#2A2C33' }
    ],
    peers: ['@oss-fan-22', '+9 more']
  },
  {
    id: 'anon-fork-31',
    handle: '@anon-fork-31',
    initials: 'AF',
    meta: '47 repos · 0 commits',
    score: 52,
    level: 'watch',
    tags: ['Fork farm', 'Empty profile'],
    age: '8 mo',
    links: 8,
    why: 'Forty-seven forks, none modified. Consistent with an archive bot rather than paid promotion, so scored as watch rather than fake.',
    factors: [
      { label: 'Profile emptiness', val: '0.68', w: '68%', c: '#8AB4F8' },
      { label: 'Fork-to-commit ratio', val: '0.59', w: '59%', c: '#8AB4F8' },
      { label: 'Cluster membership', val: '0.14', w: '14%', c: '#2A2C33' }
    ],
    peers: ['@mirror-bot-4', '+6 more']
  }
];

export const REPOS = [
  {
    name: 'dev-tools/cli',
    meta: '2,140 stars · 84 flagged stargazers',
    score: 88,
    color: '#F5C8D0',
    stars: '2,140',
    tags: ['Star burst', 'Cluster #4'],
    flagged: '84 flagged stargazers',
    path: 'M0 92 L46 90 L92 86 L138 84 L160 30 L206 26 L252 22 L298 14 L320 10'
  },
  {
    name: 'fastlane/uikit-pro',
    meta: '890 stars · 41 flagged stargazers',
    score: 81,
    color: '#F5C8D0',
    stars: '890',
    tags: ['Star burst', 'Same-day accounts'],
    flagged: '41 flagged stargazers',
    path: 'M0 94 L46 92 L92 88 L120 40 L166 36 L212 34 L258 28 L304 24 L320 22'
  },
  {
    name: 'nimbus/queue-rs',
    meta: '1,470 stars · 22 flagged stargazers',
    score: 64,
    color: '#F8DCA8',
    stars: '1,470',
    tags: ['Timing anomaly'],
    flagged: '22 flagged stargazers',
    path: 'M0 96 L46 88 L92 80 L138 74 L184 56 L230 48 L276 34 L320 26'
  },
  {
    name: 'orchard/db-lite',
    meta: '610 stars · 9 flagged stargazers',
    score: 47,
    color: '#8AB4F8',
    stars: '610',
    tags: ['Watch'],
    flagged: '9 flagged stargazers',
    path: 'M0 94 L46 90 L92 84 L138 80 L184 70 L230 64 L276 54 L320 46'
  }
];

export const MODEL_SCORES = [
  { label: 'GraphSAGE, 2 layers', val: '0.91', w: '91%', c: '#34D399', hi: true },
  { label: 'GCN, 2 layers', val: '0.86', w: '86%', c: '#8AB4F8' },
  { label: 'Gradient boosting + graph features', val: '0.79', w: '79%', c: '#F8DCA8' },
  { label: 'Profile features only, no graph', val: '0.61', w: '61%', c: '#2A2C33' }
];

// 24 hourly buckets, two rows of 12
export const HEATMAP = [
  '#17181C', '#17181C', '#1E3A2F', '#2A6B52', '#34D399', '#34D399',
  '#2A6B52', '#1E3A2F', '#17181C', '#17181C', '#1E3A2F', '#17181C',
  '#17181C', '#1E3A2F', '#2A6B52', '#34D399', '#34D399', '#2A6B52',
  '#17181C', '#17181C', '#1E3A2F', '#17181C', '#17181C', '#17181C'
];

export const AGE_BARS = [
  { x: 14, y: 30, h: 140, c: '#F5C8D0', label: '<7d' },
  { x: 64, y: 66, h: 104, c: '#F5C8D0', label: '30d' },
  { x: 114, y: 104, h: 66, c: '#F8DCA8', label: '90d' },
  { x: 164, y: 124, h: 46, c: '#F8DCA8', label: '6m' },
  { x: 214, y: 142, h: 28, c: '#2A2C33', label: '1y' },
  { x: 264, y: 152, h: 18, c: '#2A2C33', label: '2y' },
  { x: 314, y: 158, h: 12, c: '#2A2C33', label: '3y+' }
];

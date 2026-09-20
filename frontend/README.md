# StarGuard — Next.js export

The GNN fraud-detection dashboard, ported from the HTML design to Next.js (App Router).

## Run it

```bash
cd nextjs
npm install
npm run dev
```

Open http://localhost:3000.

## Structure

```
app/
  layout.js      Root layout, loads Plus Jakarta Sans + IBM Plex Mono via next/font
  page.js        Client component: page state, header, pill nav, renders the active view
  globals.css    CSS custom properties (colors) + hover states
components/
  Rail.js        Left icon rail
  KpiRow.js      Four pastel KPI tiles
  Overview.js    Area chart, verdict donut, flag reasons, clusters
  UsersTable.js  Ranked table with expandable detail rows
  Repos.js       Repo cards with star-growth curves
  GraphView.js   Star network + legend + selected node
  Analytics.js   Heatmap, age histogram, model comparison
  ui.js          Shared style objects and the Bar component
lib/
  data.js        All content and figures in one place
```

## Swapping in real data

Every number and string lives in `lib/data.js`. To wire up an API, make
`app/page.js` a server component that fetches, then pass the results down as
props — the view components are already presentational, apart from
`UsersTable` (row expand state) and `page.js` (nav state).

## Notes

- Colors are CSS custom properties in `globals.css`; component styles are inline,
  matching the original design.
- Charts are hand-authored SVG, no chart library. Replace with Recharts or
  similar if you need real scales and tooltips.
- The figures are placeholders shaped like real model output.

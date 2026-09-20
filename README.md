# StarGuard — GitHub Star-Fraud Detection with a GNN

A GitHub bot-farm / fake-star detector built on a real, trained GraphSAGE
Graph Neural Network. Full stack: Next.js dashboard + FastAPI backend +
PyTorch Geometric model.

Because scraping Upwork/Fiverr/GitHub at scale violates their ToS, the
backend generates a **statistically realistic synthetic GitHub graph** —
organic users and repos following real popularity/activity distributions,
plus 9 injected fraud rings (same-minute signups, mutual-follow rings,
fork farms, bulk-starring bursts) with **known ground-truth labels**. That
ground truth is what makes this a real, honestly-evaluated ML project
rather than a mocked-up dashboard: the GNN is actually trained with
gradient descent, evaluated on a held-out test split, and its metrics
(precision/recall/AUC) are real numbers computed from that run, not
invented ones.

```
starguard-project/
├── backend/          FastAPI + PyTorch Geometric (GraphSAGE)
│   ├── app/
│   │   ├── services/data_generator.py   synthetic graph + fraud rings
│   │   ├── services/features.py         feature engineering
│   │   ├── services/graph_builder.py    PyG graph construction
│   │   ├── services/pipeline.py         train + score + write to DB
│   │   ├── models/gnn_model.py          the GraphSAGE model itself
│   │   └── routes/                      REST API (matches frontend contract)
│   └── data/
│       ├── starguard.db     pre-built SQLite DB (ready to run immediately)
│       └── gnn_model.pt     pre-trained model weights
└── frontend/          Next.js 14 dashboard (StarGuard UI)
    ├── lib/api.js            API client
    ├── lib/useApi.js         shared fetch/loading/error hook
    └── components/           Overview, Users, Repos, Graph, Analytics
```

## Quick start

The database and model are already trained and committed, so you can run
the whole thing immediately without waiting for training.

**1. Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

**2. Frontend** (separate terminal)
```bash
cd frontend
npm install
npm run dev
```
Dashboard: http://localhost:3000

That's it — the dashboard pulls live data from the backend, which is
serving real scores computed by the trained GNN.

## Regenerating / retraining from scratch

Click **"Re-run analysis"** in the dashboard header, or run directly:
```bash
cd backend
python -m app.services.pipeline
```
This regenerates a fresh synthetic graph, retrains GraphSAGE (+ 3
baselines: GCN, gradient boosting, and a "no graph, profile features
only" logistic regression — see below), recomputes every user/repo score,
re-detects clusters, and rewrites `data/starguard.db`. Takes about
30-60 seconds on CPU.

## What's actually real here vs. what's synthetic

| Real | Synthetic |
|---|---|
| The GraphSAGE model (2-layer, PyTorch Geometric), trained with real backprop | The GitHub graph itself (scraping is against GitHub's ToS) |
| Train/val/test split methodology, threshold calibration (Platt scaling), model comparison | Specific user handles, repo names |
| Every precision/recall/AUC number in the Analytics tab | — |
| The feature engineering (account age, star-burst timing, clustering coefficient, mutual-follow density, etc.) | — |

The synthetic generator (`app/services/data_generator.py`) deliberately
makes ~30% of each fraud ring "sophisticated" — real-looking profiles
(repos, commits, followers, older accounts) that only the **graph
structure** (shared burst timing, co-starring, mutual follows) gives
away, not raw profile stats. That's why the Analytics tab shows a real
gap between the graph-based models and the profile-only baseline — it's
demonstrating something true about GNNs, not a made-up number.

## API contract

See `backend/app/routes/` for all endpoints. Summary:

| Endpoint | Purpose |
|---|---|
| `GET /api/stats` | Homepage KPIs, flag reasons, top clusters |
| `GET /api/users` | Paginated, sortable, filterable suspicious users |
| `GET /api/users/{id}` | Full user detail (starred repos, peers, timeline) |
| `GET /api/repos` | Paginated suspicious repositories |
| `GET /api/repos/{owner}/{repo}` | Repo detail + suspicious stargazers |
| `GET /api/graph` | Nodes/edges for the largest coordinated cluster |
| `GET /api/analytics` | Model comparison, activity heatmap, age distribution |
| `POST /api/analysis/run` | Kick off a full regenerate + retrain |
| `GET /api/analysis/{id}/status` | Poll that run's status |
| `POST /api/export` | CSV export of users or repos |

## Testing on real GitHub data

`scripts/run_real_data_test.py` points the already-trained model at REAL,
live GitHub accounts. It is a transfer check, not a validated evaluation —
nothing it reads has a ground-truth label.

**1. Get a token** (2 minutes, free). Go to
https://github.com/settings/tokens → *Generate new token (classic)*. You
do **not** need to tick any scopes — this only reads public data. Copy the
token and set it:

```bash
export GITHUB_TOKEN=ghp_xxx          # macOS/Linux
$env:GITHUB_TOKEN = "ghp_xxx"        # Windows PowerShell
```

Never put a real token in `.env.example` — that file is a committed
template. Put it in `.env` (git-ignored) or the environment.

**2. Run it**

```bash
cd backend
python scripts/run_real_data_test.py
```

Defaults are deliberately small to stay well under the rate limit: 5 repos
and at most 150 profile lookups, about 100 of your 5,000 hourly requests.
Override with `--repos owner/repo ...` and `--max-profiles N`.

**3. Read the output**

| File | Contents |
|---|---|
| `data/real_test_results.csv` | every account checked, both scores, and which fields were approximated |
| `data/real_test_summary.md` | plain-English summary of what got flagged |

### Why this does not use the stargazers endpoint

On **2026-06-30 GitHub restricted the starring endpoints**: `/stargazers`
and `/subscribers` are now limited to a repo's admins and collaborators,
returning 404 when authenticated and 401 when not, for any repo you do not
own. No token scope changes this. The GraphQL `stargazers` connection is
restricted the same way but fails *silently* — it returns an empty edge
list and `totalCount: 0` while the sibling `stargazerCount` still reports
the true total, so a naive fetcher reads "no stargazers" instead of
erroring.

`fetch_stargazers()` therefore reads `WatchEvent` from the public Events
feed instead, which is GitHub's name for "this account just starred this
repo" and still carries the actor login and an exact timestamp. It suits
burst detection better anyway: `/stargazers` paged oldest-first, so recent
stars — the ones that matter — were buried on the last page. The feed
retains ~300 events and ~90 days per repo.

### How the two scores differ

`rule_based_score` is a transparent 0-100 threshold check with a stated
reason for every point. **This is the number to trust.**

`gnn_confidence_experimental` is the raw sigmoid from `data/gnn_model.pt`,
which was trained only on the synthetic graph. Known limits, all surfaced
per-row in the `approximated_fields` column:

- The Platt calibrator `pipeline.py` fits is discarded (only the
  `state_dict` is saved), so this is **uncalibrated** and not on the same
  scale as the dashboard's 0-100 bands.
- `mutual_follow_density` is left at 0.0 rather than spending one request
  per account crawling the follow graph.
- `star_burst_score` and `cluster_membership` only see the sampled repos,
  so both are systematic under-estimates.

On the first real run the GNN scores compressed into 0.17-0.47 and never
crossed 0.5, flagging nothing at the dashboard's 40/60/80 bands. Of 150
accounts only 11 had co-star edges, and the graph moved every one of them
*down* (mean -0.14): mean-aggregation pulls a node toward its neighbours,
and on real data a 3-hour co-star overlap mostly catches genuine
enthusiasts browsing a niche rather than a bot ring. Treat the synthetic
co-star fingerprint as an artifact of `data_generator.py`, not a property
of real bot behaviour.

## Extending this to real GitHub data

If you want to *train* on real data rather than just score against it,
swap out `data_generator.py` for a fetcher that builds the same shape of
graph (`users`, `repos`, `starred`/`follows`/`forked` edges with
timestamps), and the rest of the pipeline (feature engineering, GNN
training, scoring, API) works unchanged.

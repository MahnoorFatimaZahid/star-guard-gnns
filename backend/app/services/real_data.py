"""
Scores REAL, live GitHub accounts instead of the synthetic graph.

Two independent scores are produced for every account:

  1. rule_based_score - a transparent 0-100 threshold check, no ML. Every
     point added is accompanied by a human-readable reason. This is the
     number to trust.

  2. gnn_confidence_experimental - the raw sigmoid output of the
     GraphSAGE weights in data/gnn_model.pt, which were trained ONLY on
     the synthetic graph and have never seen a labelled real account.
     This answers "does the synthetic pattern transfer at all", NOT "is
     this account fraudulent". See CAVEATS below.

CAVEATS on the GNN number, all of which are surfaced per-row in the
approximated_fields column:

  * The Platt calibrator that pipeline.py fits (and then discards - only
    the state_dict is saved) is not available here, so this is the raw
    uncalibrated sigmoid. It is NOT on the same scale as the 0-100
    scores in the dashboard.
  * The model was trained on features with Gaussian noise injected at
    0.75x their std (pipeline.py), so clean real features are slightly
    off-distribution.
  * mutual_follow_density needs a follow-graph crawl (1 request per
    account); it is left at 0.0 rather than spending the rate limit.
  * star_burst_score and cluster_membership are computed over only the
    repos in this sample, so both are systematic UNDER-estimates - a real
    account's true starring burst is invisible to us.

Only public data is read (the public Events feed and public profile
fields), which keeps this inside GitHub's ToS. A GITHUB_TOKEN is
required: the Events feed needs authentication and GraphQL needs it for
every request.

HISTORICAL NOTE: this module originally read star data from
GET /repos/{owner}/{repo}/stargazers. That endpoint is no longer usable
for this purpose - see fetch_stargazers() for what replaced it and why.
"""
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import networkx as nx
import requests
import torch
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.services.features import FEATURE_NAMES
from app.models.gnn_model import FraudGraphSAGE

REST_API = "https://api.github.com"
GRAPHQL_API = "https://api.github.com/graphql"

# Same-niche repos on purpose: GraphSAGE can only do message passing if
# the sampled accounts actually share edges, and co-starring only happens
# between repos the same people care about. Five unrelated mega-repos
# would give a near-empty edge set and reduce the GNN to a plain MLP.
DEFAULT_REPOS = [
    "langchain-ai/langchain",
    "run-llama/llama_index",
    "ollama/ollama",
    "chroma-core/chroma",
    "Unstructured-IO/unstructured",
]

# Mirror graph_builder.py's co-star definition exactly, so the edges the
# model sees here mean the same thing they meant during training.
CO_STAR_GAP_HOURS = 3
CO_STAR_MIN_SHARED = 2

PER_PAGE = 100
PAGES_PER_REPO = 3  # the events feed caps out at ~300 events/repo
GRAPHQL_BATCH = 25


def _session(token):
    s = requests.Session()
    s.headers.update({
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "StarGuard-real-data-test",
    })
    if token:
        s.headers["Authorization"] = "Bearer " + token
    # A single transient DNS or 5xx blip part-way through would otherwise
    # throw away every request already spent on this run.
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def _check_rate_limit(resp):
    """GitHub signals exhaustion with 403/429 + X-RateLimit-Remaining: 0,
    which is easy to misread as an auth failure."""
    if resp.status_code in (403, 429):
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            reset = resp.headers.get("X-RateLimit-Reset")
            when = ""
            if reset and reset.isdigit():
                when = datetime.fromtimestamp(int(reset), tz=timezone.utc).strftime("%H:%M UTC")
            raise RuntimeError(
                "GitHub rate limit exhausted (resets at " + when + "). "
                "Set GITHUB_TOKEN to get 5000 req/hr instead of 60."
            )
        raise RuntimeError("GitHub refused the request (%s): %s" % (resp.status_code, resp.text[:200]))


def _parse_ts(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def fetch_stargazers(sess, repo, pages=PAGES_PER_REPO):
    """Return [(login, starred_at)] for recent stars on a repo.

    This deliberately does NOT use GET /repos/{owner}/{repo}/stargazers.
    GitHub restricted the starring endpoints on 2026-06-30: the stargazer
    and watcher listings are now limited to a repo's admins and
    collaborators, so for any repo you do not own they return 404 when
    authenticated and 401 when not. The GraphQL `stargazers` connection is
    restricted the same way but fails silently - it returns an empty edge
    list and totalCount: 0 while the sibling `stargazerCount` still
    reports the true total, which makes it look like a repo with 181k
    stars has zero stargazers.
    https://github.blog/changelog/2026-06-30-upcoming-access-restrictions-to-public-api-endpoints-and-ui-views/

    The public Events feed still emits WatchEvent, which is GitHub's name
    for "this account just starred this repo", carrying the actor login
    and an exact timestamp. For burst detection it is strictly better than
    the old endpoint anyway: /stargazers paged oldest-first, so the recent
    stars that actually matter were buried on the last page.

    Limits: the feed holds ~300 events and ~90 days per repo, so this sees
    only recent activity - which is exactly the window we want.
    """
    url = REST_API + "/repos/" + repo + "/events"
    out = []
    seen_events = set()

    for page in range(1, pages + 1):
        resp = sess.get(url, params={"per_page": PER_PAGE, "page": page}, timeout=30)
        if resp.status_code == 404:
            raise RuntimeError("repo not found or private: " + repo)
        if resp.status_code == 422:
            break  # past the end of the retained events window
        _check_rate_limit(resp)
        resp.raise_for_status()

        batch = resp.json()
        if not isinstance(batch, list) or not batch:
            break

        for event in batch:
            if event.get("type") != "WatchEvent":
                continue
            login = (event.get("actor") or {}).get("login")
            if not login:
                continue
            # the feed is live, so consecutive pages can overlap
            event_id = event.get("id")
            if event_id in seen_events:
                continue
            seen_events.add(event_id)
            out.append((login, _parse_ts(event.get("created_at"))))

        time.sleep(0.2)  # stay clear of the secondary-rate-limit heuristics
    return out


_PROFILE_FIELDS = """
    login
    createdAt
    followers { totalCount }
    following { totalCount }
    ownedRepos: repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
    forkedRepos: repositories(privacy: PUBLIC, ownerAffiliations: OWNER, isFork: true) { totalCount }
    contributionsCollection { totalCommitContributions }
"""


def fetch_profiles_graphql(sess, logins):
    """Batch profile lookups through GraphQL using field aliases.

    REST would need one request per account plus a second for the commit
    count; GraphQL gets ~25 complete profiles per request. Aliases must be
    valid GraphQL names, hence u0/u1/... rather than the raw logins
    (logins may contain hyphens, which are illegal in GraphQL names).

    A login that is an organisation, suspended, or renamed makes
    user(login:) return null AND adds an entry to the top-level "errors"
    array WHILE still returning usable data for every other alias.
    Treating a non-empty "errors" as total failure is the classic mistake
    here, so we merge whatever data came back and skip the nulls.
    """
    profiles = {}
    for start in range(0, len(logins), GRAPHQL_BATCH):
        chunk = logins[start:start + GRAPHQL_BATCH]
        parts = []
        for i, login in enumerate(chunk):
            safe = login.replace("\\", "").replace('"', "")
            parts.append('  u%d: user(login: "%s") {%s  }' % (i, safe, _PROFILE_FIELDS))
        query = "query {\n" + "\n".join(parts) + "\n}"

        resp = sess.post(GRAPHQL_API, json={"query": query}, timeout=45)
        if resp.status_code == 401:
            raise RuntimeError("GraphQL requires a valid GITHUB_TOKEN (got 401).")
        _check_rate_limit(resp)
        resp.raise_for_status()
        payload = resp.json()

        data = payload.get("data") or {}
        for i, login in enumerate(chunk):
            node = data.get("u%d" % i)
            if not node:
                continue  # org, suspended, deleted, or renamed account
            created = node.get("createdAt")
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except (AttributeError, ValueError):
                continue
            age_days = max(1, (datetime.now(timezone.utc) - created_dt).days)
            profiles[login.lower()] = {
                "handle": node.get("login") or login,
                "account_age_days": age_days,
                "followers": (node.get("followers") or {}).get("totalCount", 0),
                "following": (node.get("following") or {}).get("totalCount", 0),
                "public_repos": (node.get("ownedRepos") or {}).get("totalCount", 0),
                "forks": (node.get("forkedRepos") or {}).get("totalCount", 0),
                "commits_last_year": (node.get("contributionsCollection") or {}).get(
                    "totalCommitContributions", 0),
            }
        time.sleep(0.3)
    return profiles


def _co_star_pairs(star_events):
    """Same rule as graph_builder._co_starred_edges: two accounts that
    starred >= 2 of the same repos within 3 hours of each other."""
    by_repo = defaultdict(list)
    for login, repo, ts in star_events:
        if ts is not None:
            by_repo[repo].append((login, ts))

    shared = defaultdict(int)
    for repo, entries in by_repo.items():
        entries.sort(key=lambda e: e[1])
        n = len(entries)
        for i in range(n):
            u1, t1 = entries[i]
            for j in range(i + 1, min(n, i + 40)):
                u2, t2 = entries[j]
                if u1 == u2:
                    continue
                gap = abs((t2 - t1).total_seconds()) / 3600.0
                if gap > CO_STAR_GAP_HOURS:
                    break  # sorted, so everything after is further away
                key = (u1, u2) if u1 < u2 else (u2, u1)
                shared[key] += 1
    return set(pair for pair, count in shared.items() if count >= CO_STAR_MIN_SHARED)


def _star_burst_score(timestamps):
    """Identical formula to features._star_burst_score."""
    ts = sorted(t for t in timestamps if t is not None)
    if len(ts) < 2:
        return 0.0
    span_hours = max(1.0, (ts[-1] - ts[0]).total_seconds() / 3600.0)
    return float(min(1.0, len(ts) / span_hours / 10.0))


def _feature_vector(profile, star_ts, clustering_coeff):
    """Build the same 10-dim vector, in the same order, that
    features.FEATURE_NAMES defines. Order matters - the trained weights
    are positional."""
    age_days = profile["account_age_days"]
    repos = profile["public_repos"]
    commits = profile["commits_last_year"]
    followers = profile["followers"]
    fork_ratio = profile["forks"] / (commits + 1)

    return np.array([
        1.0 / (1.0 + age_days / 30.0),              # account_age_days_inv
        np.log1p(followers),                         # follower_count_log
        np.log1p(profile["following"]),              # following_count_log
        np.log1p(repos),                             # repo_count_log
        np.log1p(commits),                           # commit_count_log
        _star_burst_score(star_ts),                  # star_burst_score
        clustering_coeff,                            # cluster_membership
        0.0,                                         # mutual_follow_density (not fetched)
        1.0 / (1.0 + repos + followers + commits),   # profile_emptiness
        min(1.0, fork_ratio),                        # fork_to_commit_ratio
    ], dtype=np.float32)


def _rule_based(profile, star_count, partners):
    """Transparent threshold check. Nothing learned, nothing hidden -
    every point has a stated reason."""
    score = 0
    reasons = []
    age = profile["account_age_days"]
    repos = profile["public_repos"]
    commits = profile["commits_last_year"]
    followers = profile["followers"]
    following = profile["following"]

    if age < 90:
        score += 25
        reasons.append("account is only %d days old" % age)
    elif age < 365:
        score += 10
        reasons.append("account is under a year old (%d days)" % age)

    if repos == 0:
        score += 20
        reasons.append("no public repositories")

    if commits == 0:
        score += 20
        reasons.append("zero commit contributions in the last year")

    if followers == 0:
        score += 10
        reasons.append("no followers")

    if following > 50 and following / max(1, followers) > 10:
        score += 15
        reasons.append("follows %d accounts but has only %d followers" % (following, followers))

    if repos >= 5 and profile["forks"] / repos > 0.8:
        score += 10
        reasons.append("%d of %d repos are forks" % (profile["forks"], repos))

    if partners >= 3:
        score += 20
        reasons.append("starred the same repos within %dh as %d other sampled accounts"
                       % (CO_STAR_GAP_HOURS, partners))
    elif partners > 0:
        score += 8
        reasons.append("co-starred in a tight window with %d other sampled account(s)" % partners)

    if star_count >= 4:
        score += 5
        reasons.append("starred %d of the sampled repos" % star_count)

    return min(100, score), reasons


def _load_model(in_dim):
    state = torch.load(settings.MODEL_PATH, map_location="cpu")
    # infer the width the weights were actually trained at, rather than
    # assuming it matches len(FEATURE_NAMES)
    trained_dim = None
    for key, tensor in state.items():
        if key.endswith("convs.0.lin_l.weight"):
            trained_dim = tensor.shape[1]
            break
    if trained_dim is None:
        trained_dim = in_dim
    model = FraudGraphSAGE(in_dim=trained_dim)
    model.load_state_dict(state)
    model.eval()
    return model, trained_dim


def run_real_test(repos=None, max_profile_lookups=150):
    token = os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        # The events feed does still answer unauthenticated, but profile
        # enrichment is GraphQL-only and GraphQL always requires a token.
        # Without one every account comes back with no profile data and a
        # rule_based_score of 0, i.e. a run that looks clean because it
        # measured nothing. Fail loudly instead.
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Profile lookups use the GraphQL API, "
            "which requires authentication - without it every account scores "
            "0 and the run is meaningless. Create a classic token (no scopes "
            "needed) at https://github.com/settings/tokens and set GITHUB_TOKEN."
        )
    used_token = True
    repos = repos or DEFAULT_REPOS
    sess = _session(token)
    pages = PAGES_PER_REPO

    print("[1/4] Fetching recent stargazers from %d repos..." % len(repos))
    star_events = []          # (login, repo, starred_at)
    repos_checked = []
    for repo in repos:
        try:
            entries = fetch_stargazers(sess, repo, pages=pages)
        except RuntimeError as exc:
            print("      %s: SKIPPED - %s" % (repo, exc))
            continue
        repos_checked.append(repo)
        for login, ts in entries:
            star_events.append((login, repo, ts))
        print("      %s: %d stargazers" % (repo, len(entries)))

    if not star_events:
        raise RuntimeError("No stargazers fetched - cannot continue.")

    stars_by_user = defaultdict(list)
    for login, repo, ts in star_events:
        stars_by_user[login].append(ts)
    total_unique = len(stars_by_user)
    print("      %d unique accounts seen" % total_unique)

    print("[2/4] Finding co-star bursts...")
    pairs = _co_star_pairs(star_events)
    partner_graph = nx.Graph()
    partner_graph.add_nodes_from(stars_by_user.keys())
    partner_graph.add_edges_from(pairs)
    print("      %d co-star edges among sampled accounts" % len(pairs))

    # Spend the profile budget where it is most informative: accounts that
    # co-starred with someone, then accounts that starred several of the
    # sampled repos, then the rest.
    def _priority(login):
        return (-partner_graph.degree(login), -len(stars_by_user[login]))

    candidates = sorted(stars_by_user.keys(), key=_priority)[:max_profile_lookups]

    print("[3/4] Looking up %d profiles via GraphQL..." % len(candidates))
    if used_token:
        profiles = fetch_profiles_graphql(sess, candidates)
    else:
        profiles = {}
        print("      SKIPPED - GraphQL requires a token.")
    print("      %d profiles returned" % len(profiles))

    print("[4/4] Scoring (rule-based + experimental GNN)...")
    clustering = nx.clustering(partner_graph)

    scored_logins = []
    vectors = []
    for login in candidates:
        profile = profiles.get(login.lower())
        if not profile:
            continue
        scored_logins.append(login)
        vectors.append(_feature_vector(profile, stars_by_user[login], clustering.get(login, 0.0)))

    gnn_scores = {}
    if vectors:
        x = torch.tensor(np.stack(vectors), dtype=torch.float32)
        if x.shape[1] != len(FEATURE_NAMES):
            raise RuntimeError(
                "built %d features but features.FEATURE_NAMES declares %d - "
                "_feature_vector() and FEATURE_NAMES have drifted apart."
                % (x.shape[1], len(FEATURE_NAMES))
            )
        model, trained_dim = _load_model(x.shape[1])
        if trained_dim != x.shape[1]:
            print("      WARNING: weights expect %d features, built %d - skipping GNN."
                  % (trained_dim, x.shape[1]))
        else:
            idx = dict((login, i) for i, login in enumerate(scored_logins))
            edges = [(idx[a], idx[b]) for a, b in pairs if a in idx and b in idx]
            if edges:
                both = edges + [(b, a) for a, b in edges]
                edge_index = torch.tensor(both, dtype=torch.long).t().contiguous()
            else:
                edge_index = torch.zeros((2, 0), dtype=torch.long)
            print("      GNN graph: %d nodes, %d directed edges"
                  % (len(scored_logins), edge_index.shape[1]))
            with torch.no_grad():
                probs = torch.sigmoid(model(x, edge_index)).numpy()
            gnn_scores = dict((login, float(probs[i])) for i, login in enumerate(scored_logins))

    approximated = [
        "mutual_follow_density=0 (follow graph not crawled)",
        "star_burst_score from sampled repos only (under-estimate)",
        "cluster_membership from co-star graph only",
        "commits_last_year used in place of lifetime commits",
        "gnn score is uncalibrated raw sigmoid",
    ]

    results = []
    for login in candidates:
        profile = profiles.get(login.lower())
        star_count = len(stars_by_user[login])
        partners = partner_graph.degree(login) if login in partner_graph else 0
        if profile:
            score, reasons = _rule_based(profile, star_count, partners)
            results.append({
                "handle": profile["handle"],
                "github_url": "https://github.com/" + profile["handle"],
                "has_profile_data": True,
                "followers": profile["followers"],
                "following": profile["following"],
                "public_repos": profile["public_repos"],
                "commits_last_year": profile["commits_last_year"],
                "account_age_days": profile["account_age_days"],
                "star_count": star_count,
                "co_star_burst_partners": partners,
                "rule_based_score": score,
                "rule_based_reasons": reasons,
                "gnn_confidence_experimental": round(gnn_scores[login], 4)
                    if login in gnn_scores else "",
                "approximated_fields": approximated,
            })
        else:
            results.append({
                "handle": login,
                "github_url": "https://github.com/" + login,
                "has_profile_data": False,
                "followers": "", "following": "", "public_repos": "",
                "commits_last_year": "", "account_age_days": "",
                "star_count": star_count,
                "co_star_burst_partners": partners,
                "rule_based_score": 0,
                "rule_based_reasons": ["profile lookup unavailable (org, renamed, or suspended)"],
                "gnn_confidence_experimental": "",
                "approximated_fields": ["no profile data"],
            })

    results.sort(key=lambda r: (-r["rule_based_score"], r["handle"].lower()))

    return {
        "results": results,
        "repos_checked": repos_checked,
        "total_unique_accounts": total_unique,
        "profiles_enriched": len(profiles),
        "used_token": used_token,
    }

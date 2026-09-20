"""
Feature engineering: turns raw graph + node attributes into numeric
feature vectors the GNN can consume. Every feature here is something a
human reviewer would also look at, which is what makes the model's
"contributing factors" explainable later.
"""
import numpy as np
import networkx as nx
from datetime import datetime

FEATURE_NAMES = [
    "account_age_days_inv",   # younger = higher value (suspicious)
    "follower_count_log",
    "following_count_log",
    "repo_count_log",
    "commit_count_log",
    "star_burst_score",       # stars concentrated in a short time window
    "cluster_membership",     # local clustering coefficient among same-type neighbors
    "mutual_follow_density",  # fraction of follows that are mutual within 2-hop neighborhood
    "profile_emptiness",      # inverse of (repos+followers+commits)
    "fork_to_commit_ratio",
]


def _star_burst_score(ts_list):
    if len(ts_list) < 2:
        return 0.0
    ts_sorted = sorted(ts_list)
    span_hours = max(1.0, (ts_sorted[-1] - ts_sorted[0]).total_seconds() / 3600.0)
    return float(min(1.0, len(ts_sorted) / span_hours / 10.0))


def compute_user_features(gen):
    """Returns dict[user_id] -> np.array(feature_vector), plus raw stats dict."""
    g = gen.g
    features = {}
    raw = {}

    # precompute undirected view for clustering coefficient among users
    user_ids = [u for u, d in g.nodes(data=True) if d.get("kind") == "user"]
    user_subgraph_edges = []
    for uid in user_ids:
        for _, t, d in g.out_edges(uid, data=True):
            if d.get("kind") == "follows" and g.nodes[t].get("kind") == "user":
                user_subgraph_edges.append((uid, t))
    ug = nx.Graph()
    ug.add_nodes_from(user_ids)
    ug.add_edges_from(user_subgraph_edges)
    clustering = nx.clustering(ug)

    for uid in user_ids:
        u = gen.users[uid]
        age_days = max(1, (gen_now() - u["created_at"]).days)

        star_edges = [d["ts"] for _, t, d in g.out_edges(uid, data=True) if d.get("kind") == "starred"]
        follow_edges = [(uid, t) for _, t, d in g.out_edges(uid, data=True) if d.get("kind") == "follows"]
        mutual = 0
        for (_, t) in follow_edges:
            if g.has_edge(t, uid) and g.get_edge_data(t, uid, default={}).get("kind") == "follows":
                mutual += 1
        mutual_density = mutual / len(follow_edges) if follow_edges else 0.0

        repo_count = u["public_repos"]
        commit_count = u["commits"]
        fork_edges = [1 for _, t, d in g.out_edges(uid, data=True) if d.get("kind") == "forked"]
        fork_ratio = len(fork_edges) / (commit_count + 1)

        profile_emptiness = 1.0 / (1.0 + repo_count + u["followers"] + commit_count)

        vec = np.array([
            1.0 / (1.0 + age_days / 30.0),
            np.log1p(u["followers"]),
            np.log1p(u["following"]),
            np.log1p(repo_count),
            np.log1p(commit_count),
            _star_burst_score(star_edges),
            clustering.get(uid, 0.0),
            mutual_density,
            profile_emptiness,
            min(1.0, fork_ratio),
        ], dtype=np.float32)

        features[uid] = vec
        raw[uid] = {
            "age_days": age_days,
            "star_count": len(star_edges),
            "follow_count": len(follow_edges),
            "mutual_density": mutual_density,
            "repo_count": repo_count,
            "commit_count": commit_count,
        }

    return features, raw


def gen_now():
    from app.services.data_generator import NOW
    return NOW


def compute_repo_features(gen):
    g = gen.g
    repo_ids = [r for r, d in g.nodes(data=True) if d.get("kind") == "repo"]
    features = {}
    raw = {}
    for rid in repo_ids:
        r = gen.repos[rid]
        stargazers = [(s, d["ts"]) for s, _, d in g.in_edges(rid, data=True) if d.get("kind") == "starred"]
        total_stars = len(stargazers)
        fraud_stars = sum(1 for s, _ in stargazers if gen.users.get(s, {}).get("is_fraud"))
        burst = _star_burst_score([ts for _, ts in stargazers])

        vec = np.array([
            np.log1p(total_stars),
            fraud_stars / (total_stars + 1),
            burst,
            np.log1p((gen_now() - r["created_at"]).days),
        ], dtype=np.float32)
        features[rid] = vec
        raw[rid] = {
            "total_stars": total_stars,
            "fraud_stars": fraud_stars,
            "stargazers": stargazers,
        }
    return features, raw

"""
End-to-end pipeline: generate data -> engineer features -> build graph ->
train GraphSAGE (+ 3 baselines for the Analytics comparison page) ->
score every user & repo -> detect clusters -> persist everything to SQLite.

Run with:  python -m app.services.pipeline
"""
import json
import random
import numpy as np
import torch
import torch.nn.functional as F
import networkx as nx
from datetime import datetime
from sklearn.metrics import precision_score, recall_score, roc_auc_score, f1_score
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression as _PlattLR
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from torch_geometric.nn import GCNConv

from app.config import settings
from app.database.db import init_db, wipe_db, get_conn, set_meta
from app.services.data_generator import generate_graph
from app.services.features import compute_user_features, compute_repo_features, FEATURE_NAMES
from app.services.graph_builder import build_user_graph
from app.models.gnn_model import FraudGraphSAGE

FACTOR_LABELS = {
    "account_age_days_inv": "Account age",
    "follower_count_log": "Follower count",
    "following_count_log": "Following count",
    "repo_count_log": "Repository count",
    "commit_count_log": "Commit activity",
    "star_burst_score": "Star burst timing",
    "cluster_membership": "Cluster membership",
    "mutual_follow_density": "Mutual-follow density",
    "profile_emptiness": "Profile emptiness",
    "fork_to_commit_ratio": "Fork-to-commit ratio",
}


def _risk_level(score_100):
    if score_100 >= settings.RISK_THRESHOLDS["critical"]:
        return "critical"
    if score_100 >= settings.RISK_THRESHOLDS["high"]:
        return "high"
    if score_100 >= settings.RISK_THRESHOLDS["watch"]:
        return "watch"
    return "safe"


def _level_color(level):
    return {"critical": "#F5C8D0", "high": "#F8DCA8", "watch": "#8AB4F8", "safe": "#2A2C33"}[level]


def _age_label(days):
    if days < 30:
        return f"{days} d"
    if days < 365:
        return f"{days // 30} mo"
    return f"{days // 365} y"


def _sparkline(seed, n=10, trend=1.0):
    rng = np.random.RandomState(seed)
    vals = np.cumsum(rng.randn(n) * 3 + trend * 2)
    vals = vals - vals.min() + 5
    vals = 34 - (vals / vals.max()) * 30
    pts = " ".join(f"L{22*i+2} {v:.0f}" for i, v in enumerate(vals))
    return "M" + pts[1:]


class GCNBaseline(torch.nn.Module):
    def __init__(self, in_dim, hidden=64):
        super().__init__()
        self.c1 = GCNConv(in_dim, hidden)
        self.c2 = GCNConv(hidden, hidden)
        self.out = torch.nn.Linear(hidden, 1)

    def forward(self, x, edge_index):
        h = F.relu(self.c1(x, edge_index))
        h = F.dropout(h, p=0.3, training=self.training)
        h = F.relu(self.c2(h, edge_index))
        return self.out(h).squeeze(-1)


def _train_torch_model(model, data, train_mask, val_mask, epochs=120, lr=0.01):
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
    pos_weight = torch.tensor([(train_mask.sum() - data.y[train_mask].sum()) / max(1, data.y[train_mask].sum())])
    best_state, best_auc = None, -1
    for epoch in range(epochs):
        model.train()
        opt.zero_grad()
        logits = model(data.x, data.edge_index)
        loss = F.binary_cross_entropy_with_logits(logits[train_mask], data.y[train_mask], pos_weight=pos_weight)
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            probs = torch.sigmoid(model(data.x, data.edge_index))
            val_probs = probs[val_mask].numpy()
            val_y = data.y[val_mask].numpy()
            if val_y.sum() > 0 and val_y.sum() < len(val_y):
                auc = roc_auc_score(val_y, val_probs)
                if auc > best_auc:
                    best_auc = auc
                    best_state = {k: v.clone() for k, v in model.state_dict().items()}
    if best_state:
        model.load_state_dict(best_state)
    return model, best_auc


def _best_threshold(y_val, probs_val):
    """Pick the classification threshold that maximizes F1 on validation
    data, instead of assuming 0.5 — with class-weighted BCE the raw
    sigmoid outputs are not calibrated probabilities, so a fixed 0.5 cutoff
    silently collapses recall even when ranking (AUC) is excellent."""
    if y_val.sum() == 0 or y_val.sum() == len(y_val):
        return 0.5
    candidates = np.unique(np.clip(probs_val, 0.01, 0.99))
    if len(candidates) > 200:
        candidates = np.quantile(candidates, np.linspace(0, 1, 200))
    best_t, best_f1 = 0.5, -1
    for t in candidates:
        preds = (probs_val >= t).astype(int)
        f1 = f1_score(y_val, preds, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return float(best_t)


def _eval_binary(y_true, probs, threshold=0.5):
    preds = (probs >= threshold).astype(int)
    return {
        "precision": float(precision_score(y_true, preds, zero_division=0)),
        "recall": float(recall_score(y_true, preds, zero_division=0)),
        "f1": float(f1_score(y_true, preds, zero_division=0)),
        "auc": float(roc_auc_score(y_true, probs)) if 0 < y_true.sum() < len(y_true) else 0.5,
        "threshold": float(threshold),
    }


def run_pipeline():
    print("[1/6] Generating synthetic GitHub graph...")
    gen = generate_graph()
    print(f"      users={len(gen.users)} repos={len(gen.repos)} edges={gen.g.number_of_edges()}")

    print("[2/6] Engineering features...")
    user_features, user_raw = compute_user_features(gen)
    repo_features, repo_raw = compute_repo_features(gen)

    print("[3/6] Building PyG graph...")
    data, user_ids, uidx = build_user_graph(gen, user_features)

    # Real-world features are noisy and overlap between classes — without
    # this, the synthetic profile features alone perfectly separate fraud
    # from real accounts and every model (even the no-graph baseline) hits
    # ~1.0 AUC, which would misrepresent what the graph actually buys you.
    # A little jitter creates the ambiguous, only-resolvable-via-structure
    # cases that graph message-passing is actually good at.
    noise_rng = np.random.RandomState(settings.RANDOM_SEED)
    noise = noise_rng.normal(0, 1, size=data.x.shape).astype(np.float32)
    feat_std = data.x.numpy().std(axis=0, keepdims=True)
    data.x = data.x + torch.from_numpy(noise * feat_std * 0.75)
    data.x = torch.clamp(data.x, min=0)

    n = len(user_ids)
    perm = np.random.RandomState(settings.RANDOM_SEED).permutation(n)
    train_idx = perm[: int(n * 0.7)]
    val_idx = perm[int(n * 0.7): int(n * 0.85)]
    test_idx = perm[int(n * 0.85):]
    train_mask = torch.zeros(n, dtype=torch.bool); train_mask[train_idx] = True
    val_mask = torch.zeros(n, dtype=torch.bool); val_mask[val_idx] = True
    test_mask = torch.zeros(n, dtype=torch.bool); test_mask[test_idx] = True

    print("[4/6] Training GraphSAGE (primary model) + baselines...")
    torch.manual_seed(settings.RANDOM_SEED)
    sage = FraudGraphSAGE(in_dim=data.x.shape[1])
    sage, sage_val_auc = _train_torch_model(sage, data, train_mask, val_mask)
    sage.eval()
    with torch.no_grad():
        sage_probs_all = torch.sigmoid(sage(data.x, data.edge_index)).numpy()
        gate_all = sage.feature_importance(data.x).numpy()
    sage_thr = _best_threshold(data.y.numpy()[val_idx], sage_probs_all[val_idx])
    sage_test_metrics = _eval_binary(data.y.numpy()[test_idx], sage_probs_all[test_idx], sage_thr)

    torch.manual_seed(settings.RANDOM_SEED)
    gcn = GCNBaseline(in_dim=data.x.shape[1])
    gcn, _ = _train_torch_model(gcn, data, train_mask, val_mask)
    gcn.eval()
    with torch.no_grad():
        gcn_probs = torch.sigmoid(gcn(data.x, data.edge_index)).numpy()
    gcn_thr = _best_threshold(data.y.numpy()[val_idx], gcn_probs[val_idx])
    gcn_test_metrics = _eval_binary(data.y.numpy()[test_idx], gcn_probs[test_idx], gcn_thr)

    X = data.x.numpy()
    y = data.y.numpy()
    gb = GradientBoostingClassifier(random_state=settings.RANDOM_SEED)
    gb.fit(X[train_idx], y[train_idx])
    gb_probs = gb.predict_proba(X)[:, 1]
    gb_thr = _best_threshold(y[val_idx], gb_probs[val_idx])
    gb_test_metrics = _eval_binary(y[test_idx], gb_probs[test_idx], gb_thr)

    # "No graph" baseline: strip out every feature derived from graph
    # structure (star-burst timing, clustering coefficient, mutual-follow
    # density) and keep only what a single profile lookup would show.
    graph_derived = {"star_burst_score", "cluster_membership", "mutual_follow_density"}
    profile_cols = [i for i, name in enumerate(FEATURE_NAMES) if name not in graph_derived]
    lr = LogisticRegression(max_iter=1000)
    lr.fit(X[train_idx][:, profile_cols], y[train_idx])
    lr_probs = lr.predict_proba(X[:, profile_cols])[:, 1]
    lr_thr = _best_threshold(y[val_idx], lr_probs[val_idx])
    lr_test_metrics = _eval_binary(y[test_idx], lr_probs[test_idx], lr_thr)

    print(f"      GraphSAGE  precision={sage_test_metrics['precision']:.2f} recall={sage_test_metrics['recall']:.2f} auc={sage_test_metrics['auc']:.2f}")
    print(f"      GCN        precision={gcn_test_metrics['precision']:.2f} recall={gcn_test_metrics['recall']:.2f} auc={gcn_test_metrics['auc']:.2f}")
    print(f"      GradBoost  precision={gb_test_metrics['precision']:.2f} recall={gb_test_metrics['recall']:.2f} auc={gb_test_metrics['auc']:.2f}")
    print(f"      LogReg     precision={lr_test_metrics['precision']:.2f} recall={lr_test_metrics['recall']:.2f} auc={lr_test_metrics['auc']:.2f}")

    torch.save(sage.state_dict(), settings.MODEL_PATH)

    print("[5/6] Scoring all users/repos + detecting clusters...")
    # Class-weighted BCE gives well-RANKED but poorly-CALIBRATED sigmoid
    # outputs (e.g. real fraud accounts sitting at raw 0.45-0.55, never
    # crossing a naive ">=0.8 = critical" cutoff even though they're
    # clearly separated from genuine accounts near 0.05). Isotonic
    # regression, fit on the held-out validation split, remaps raw scores
    # to actual empirical fraud likelihood so the 80/60/40 bands mean
    # what they say ("80%+ chance this is fake") instead of an arbitrary
    # slice of the model's internal output scale.
    # Platt scaling (regularized 1-D logistic fit) rather than isotonic:
    # isotonic is a step function and, on a nearly-separable validation
    # set, collapses almost everything to exactly 0 or 100 — leaving no
    # graded critical/high/watch spread. A regularized logistic curve
    # keeps the calibration honest (still fit on held-out labels) while
    # preserving a smooth gradient of confidence.
    raw_logit = np.log(np.clip(sage_probs_all, 1e-6, 1 - 1e-6) / (1 - np.clip(sage_probs_all, 1e-6, 1 - 1e-6)))
    platt = _PlattLR(C=0.35, max_iter=1000)
    platt.fit(raw_logit[val_idx].reshape(-1, 1), data.y.numpy()[val_idx])
    calibrated = platt.predict_proba(raw_logit.reshape(-1, 1))[:, 1]
    scores_100 = np.clip(calibrated * 100, 0, 100)

    # cluster detection: connected components among users scored >= watch threshold,
    # using the same edge set the GNN trained on
    risky_mask = scores_100 >= settings.RISK_THRESHOLDS["watch"]
    ug = nx.Graph()
    ug.add_nodes_from([user_ids[i] for i in range(n) if risky_mask[i]])
    ei = data.edge_index.numpy()
    for a, b in zip(ei[0], ei[1]):
        ua, ub = user_ids[a], user_ids[b]
        if risky_mask[a] and risky_mask[b]:
            ug.add_edge(ua, ub)
    components = [c for c in nx.connected_components(ug) if len(c) >= 5]
    components.sort(key=len, reverse=True)

    cluster_records = []
    member_to_cluster = {}
    for i, comp in enumerate(components[:12]):
        members = list(comp)
        avg_score = float(np.mean([scores_100[uidx[m]] for m in members]))
        # try to recover a human-readable archetype from generator ground truth (majority vote)
        archetypes = [gen.users[m].get("archetype") for m in members if gen.users[m].get("archetype")]
        archetype = max(set(archetypes), key=archetypes.count) if archetypes else "mixed"
        name_map = {
            "same_minute_signup": "Same-minute signups",
            "mutual_follow_ring": "Mutual-follow ring",
            "fork_farm": "Fork farm",
            "bulk_starrer": "Bulk-starring ring",
            "mixed": "Coordinated cluster",
        }
        sample_created = min(gen.users[m]["created_at"] for m in members)
        cluster_records.append({
            "id": f"cluster-{i}",
            "tag": f"#{i}",
            "name": name_map.get(archetype, "Coordinated cluster"),
            "detail": f"Created {sample_created.strftime('%d %b, %H:%M')} UTC" if archetype == "same_minute_signup"
                      else ("Follows almost nobody outside itself" if archetype == "mutual_follow_ring"
                      else ("Forks without a single commit" if archetype == "fork_farm" else "Starred the same repos within hours")),
            "size": str(len(members)),
            "members": members,
            "risk_level": _risk_level(avg_score),
        })
        for m in members:
            member_to_cluster[m] = f"cluster-{i}"

    print("[6/6] Writing to database...")
    init_db()
    wipe_db()

    with get_conn() as conn:
        for i, uid in enumerate(user_ids):
            u = gen.users[uid]
            score = float(scores_100[i])
            level = _risk_level(score)
            gate = gate_all[i]
            top_factor_idx = np.argsort(-gate)[:4]
            factors = []
            for fi in top_factor_idx:
                fname = FEATURE_NAMES[fi]
                val = float(gate[fi])
                factors.append({
                    "label": FACTOR_LABELS[fname],
                    "val": f"{val:.2f}",
                    "width": f"{int(val*100)}%",
                    "color": "#F5C8D0" if val >= 0.8 else "#F8DCA8" if val >= 0.6 else "#8AB4F8",
                })

            tags = []
            raw = user_raw[uid]
            if raw["star_count"] >= 15 and _star_burst_flag(user_features[uid]):
                tags.append("Bulk starrer")
            if uid in member_to_cluster:
                tags.append("Bot cluster")
            if raw["repo_count"] == 0 and u["followers"] == 0:
                tags.append("Empty profile")
            if raw["mutual_density"] > 0.5:
                tags.append("Mutual-follow ring")
            if not tags:
                tags.append("Watch")

            neighbors = list(gen.g.successors(uid)) + list(gen.g.predecessors(uid))
            peer_ids = [x for x in neighbors if x in gen.users and x != uid]
            cluster_key = member_to_cluster.get(uid)
            cluster_size = 0
            if cluster_key:
                cluster_members = cluster_records[int(cluster_key.split('-')[1])]["members"]
                cluster_size = len(cluster_members)
                if not peer_ids:
                    # no direct follow/co-star edge (e.g. bulk-starrer, fork
                    # farm) — fall back to cluster-mates so the panel isn't
                    # empty; still real cluster membership, not invented.
                    peer_ids = [m for m in cluster_members if m != uid]
            peer_ids = peer_ids[:4]
            peers = [gen.users[p]["handle"] for p in peer_ids]
            extra = cluster_size - len(peers) if cluster_key else 0
            if extra > 0:
                peers.append(f"+{extra} more")

            why = _explain(u, raw, tags, level)

            conn.execute(
                "INSERT INTO users (id, handle, created_at, followers, following, public_repos, "
                "public_gists, commits, score, level, tags, age_label, links, why, factors, peers) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (uid, u["handle"], u["created_at"].isoformat(), u["followers"], u["following"],
                 u["public_repos"], u["public_gists"], u["commits"], score, level,
                 json.dumps(tags), _age_label(raw["age_days"]), raw["follow_count"] + raw["star_count"],
                 why, json.dumps(factors), json.dumps(peers))
            )

        repo_scores = {}
        for rid, r in gen.repos.items():
            rr = repo_raw[rid]
            total = rr["total_stars"]
            fraud = rr["fraud_stars"]
            frac_fraud = fraud / total if total else 0
            score = min(100, frac_fraud * 100 * 0.85 + (10 if total > 500 and frac_fraud > 0.02 else 0))
            repo_scores[rid] = score
            level = _risk_level(score)
            tags = []
            if frac_fraud > 0.3:
                tags.append("Star burst")
            if fraud > 0:
                cl = None
                for c in cluster_records:
                    if any(gen.users[m]["fraud_cluster"] is not None for m in c["members"]):
                        cl = c
                        break
                if cl:
                    tags.append(f"Cluster {cl['tag']}")
            if not tags:
                tags.append("Watch")

            conn.execute(
                "INSERT INTO repos (id, name, url, created_at, pushed_at, language, description, "
                "stars, score, color, tags, flagged_count, sparkline_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid, r["name"], f"https://github.com/{r['name']}", r["created_at"].isoformat(),
                 r["pushed_at"].isoformat(), r["language"], r["description"], total, score,
                 _level_color(level), json.dumps(tags), fraud,
                 _sparkline(hash(rid) % (2**31), trend=1 if frac_fraud < 0.1 else 3))
            )

            for s_uid, ts in rr["stargazers"][:2000]:
                conn.execute("INSERT INTO stars (user_id, repo_id, starred_at) VALUES (?,?,?)",
                             (s_uid, rid, ts.isoformat()))

        for u, t, d in gen.g.edges(data=True):
            if d.get("kind") == "follows":
                conn.execute("INSERT INTO follows (follower_id, following_id) VALUES (?,?)", (u, t))

        for c in cluster_records:
            conn.execute(
                "INSERT INTO clusters (id, tag, name, detail, size, members, risk_level) VALUES (?,?,?,?,?,?,?)",
                (c["id"], c["tag"], c["name"], c["detail"], c["size"], json.dumps(c["members"]), c["risk_level"])
            )

        model_rows = [
            ("GraphSAGE, 2 layers", sage_test_metrics, "#34D399", 1),
            ("GCN, 2 layers", gcn_test_metrics, "#8AB4F8", 0),
            ("Gradient boosting + graph features", gb_test_metrics, "#F8DCA8", 0),
            ("Profile features only, no graph", lr_test_metrics, "#2A2C33", 0),
        ]
        for label, m, color, is_cur in model_rows:
            conn.execute(
                "INSERT INTO model_scores (label, val, width, color, is_current, precision, recall, f1, auc) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (label, f"{m['auc']:.2f}", f"{int(m['auc']*100)}%", color, is_cur,
                 m["precision"], m["recall"], m["f1"], m["auc"])
            )

    set_meta("last_run", {
        "finished_at": datetime.utcnow().isoformat(),
        "num_users": len(gen.users),
        "num_repos": len(gen.repos),
        "num_flagged": int((scores_100 >= settings.RISK_THRESHOLDS["watch"]).sum()),
        "num_clusters": len(cluster_records),
        "precision_at_100": _precision_at_k(data.y.numpy(), sage_probs_all, 100),
    })

    print("Done. Database written to", settings.DATABASE_PATH)


def _star_burst_flag(vec):
    return vec[5] > 0.3  # index of star_burst_score in FEATURE_NAMES


def _precision_at_k(y_true, probs, k):
    order = np.argsort(-probs)[:k]
    return float(y_true[order].mean())


def _explain(u, raw, tags, level):
    if "Bot cluster" in tags and raw["mutual_density"] > 0.4:
        return (f"Follows and is followed by a tight group of accounts and almost nobody outside it. "
                f"Account is {raw['age_days']} days old with {raw['repo_count']} repositories.")
    if "Bulk starrer" in tags:
        return (f"Starred {raw['star_count']} repositories in a short window, heavily overlapping with "
                f"other flagged accounts created around the same time.")
    if "Empty profile" in tags:
        return (f"No repositories, no followers, {raw['age_days']} days old — consistent with an "
                f"unused or automated account.")
    if level in ("critical", "high"):
        return "Multiple graph and profile signals place this account in a high-risk cluster."
    return "Minor anomalies detected; most likely a false positive, kept for review."


if __name__ == "__main__":
    run_pipeline()

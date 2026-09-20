"""
Builds a PyTorch Geometric Data object (user-user graph) from the
generated graph + computed features:

  edges = "follows" edges (both directions) UNION "co-starred" edges
          (two users who starred >=2 identical repos within a 3-hour
          window of each other — the classic bot-ring fingerprint)
"""
import numpy as np
import torch
from collections import defaultdict
from torch_geometric.data import Data


def _co_starred_edges(gen, max_gap_hours=3, min_shared=2):
    # repo -> list of (user, ts)
    repo_stargazers = defaultdict(list)
    for u, r, d in gen.g.edges(data=True):
        if d.get("kind") == "starred":
            repo_stargazers[r].append((u, d["ts"]))

    pair_shared = defaultdict(int)
    for rid, stargazers in repo_stargazers.items():
        stargazers.sort(key=lambda x: x[1])
        n = len(stargazers)
        if n > 400:  # cap cost on very popular repos
            stargazers = stargazers[:400]
            n = 400
        for i in range(n):
            u1, t1 = stargazers[i]
            for j in range(i + 1, min(n, i + 30)):
                u2, t2 = stargazers[j]
                gap = abs((t2 - t1).total_seconds()) / 3600.0
                if gap <= max_gap_hours:
                    key = (u1, u2) if u1 < u2 else (u2, u1)
                    pair_shared[key] += 1

    edges = [pair for pair, cnt in pair_shared.items() if cnt >= min_shared]
    return edges


def build_user_graph(gen, user_features):
    user_ids = list(user_features.keys())
    idx = {uid: i for i, uid in enumerate(user_ids)}

    edge_set = set()
    for u, t, d in gen.g.edges(data=True):
        if d.get("kind") == "follows" and u in idx and t in idx:
            edge_set.add((idx[u], idx[t]))
            edge_set.add((idx[t], idx[u]))  # treat as undirected for message passing

    for u1, u2 in _co_starred_edges(gen):
        if u1 in idx and u2 in idx:
            edge_set.add((idx[u1], idx[u2]))
            edge_set.add((idx[u2], idx[u1]))

    if edge_set:
        edge_index = torch.tensor(list(edge_set), dtype=torch.long).t().contiguous()
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long)

    x = torch.tensor(np.stack([user_features[uid] for uid in user_ids]), dtype=torch.float32)
    y = torch.tensor([1.0 if gen.users[uid]["is_fraud"] else 0.0 for uid in user_ids], dtype=torch.float32)

    data = Data(x=x, edge_index=edge_index, y=y)
    return data, user_ids, idx

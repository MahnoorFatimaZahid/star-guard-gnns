"""
Synthetic GitHub graph generator.

Real GitHub scraping is against ToS (as discussed), so this generates a
statistically realistic graph instead: normal organic users/repos following
a preferential-attachment pattern, PLUS injected fraud rings that mimic real
bot-farm behavior:

  - Same-minute signups: dozens of accounts created in one burst
  - Bulk starring: a burst of stars on a small set of repos within hours
  - Mutual-follow rings: bots follow mostly each other, not the wider graph
  - Fork farms: bulk forking with zero commits

Ground-truth fraud labels are known (we injected them), which lets us
train a real, supervised GraphSAGE model rather than faking scores.
"""
import random
import numpy as np
import networkx as nx
from datetime import datetime, timedelta
from app.config import settings

random.seed(settings.RANDOM_SEED)
np.random.seed(settings.RANDOM_SEED)

NOW = datetime(2024, 10, 19, 12, 0, 0)

ADJECTIVES = ["quick", "nimbus", "orchard", "dev", "fastlane", "star", "gh", "anon",
              "mirror", "quantum", "byte", "cloud", "vector", "proto", "nova"]
NOUNS = ["tools", "cli", "uikit", "queue", "db", "bot", "user", "fork", "star", "lib",
         "engine", "core", "api", "sdk", "runtime"]


def _rand_repo_name(i):
    return f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}/{random.choice(NOUNS)}-{i % 97}"


def _rand_handle(prefix, i):
    return f"{prefix}-{i}"


class GitHubGraphGenerator:
    def __init__(self):
        self.g = nx.DiGraph()
        self.users = {}
        self.repos = {}
        self.clusters = []

    # ---------- normal population ----------
    def _gen_normal_users(self, n):
        for i in range(n):
            age_days = int(np.random.exponential(400)) + 10
            created_at = NOW - timedelta(days=age_days)
            followers = max(0, int(np.random.lognormal(2.0, 1.3)))
            following = max(0, int(np.random.lognormal(1.8, 1.1)))
            public_repos = max(0, int(np.random.lognormal(1.3, 1.0)))
            commits = public_repos * max(1, int(np.random.lognormal(3, 1.2)))
            uid = f"user-{i}"
            self.users[uid] = {
                "id": uid,
                "handle": f"@{_rand_handle('dev', i) if i % 3 else _rand_handle('oss-fan', i)}",
                "created_at": created_at,
                "followers": followers,
                "following": following,
                "public_repos": public_repos,
                "public_gists": max(0, int(np.random.poisson(1))),
                "commits": commits,
                "is_fraud": False,
                "fraud_cluster": None,
            }
            self.g.add_node(uid, kind="user")

    def _gen_repos(self, n):
        for i in range(n):
            age_days = int(np.random.exponential(300)) + 5
            created_at = NOW - timedelta(days=age_days)
            base_stars = max(1, int(np.random.lognormal(3.5, 1.8)))
            rid = f"repo-{i}"
            self.repos[rid] = {
                "id": rid,
                "name": _rand_repo_name(i),
                "created_at": created_at,
                "pushed_at": created_at + timedelta(days=random.randint(1, age_days)),
                "language": random.choice(["Rust", "TypeScript", "Python", "Go", "C++"]),
                "description": "Open source project",
                "organic_stars": base_stars,
                "fraud_stars": 0,
            }
            self.g.add_node(rid, kind="repo")

    def _gen_organic_edges(self):
        user_ids = list(self.users.keys())
        repo_ids = list(self.repos.keys())

        # Organic stars: popularity-weighted (preferential attachment feel)
        weights = np.array([self.repos[r]["organic_stars"] for r in repo_ids], dtype=float)
        weights = weights / weights.sum()

        for uid, u in self.users.items():
            n_stars = min(len(repo_ids), max(0, int(np.random.lognormal(1.5, 1.4))))
            chosen = np.random.choice(repo_ids, size=n_stars, replace=False, p=weights) if n_stars else []
            for rid in chosen:
                ts = self.repos[rid]["created_at"] + timedelta(
                    days=random.randint(0, max(1, (NOW - self.repos[rid]["created_at"]).days))
                )
                self.g.add_edge(uid, rid, kind="starred", ts=ts)

        # Organic follows: small-world-ish, random but sparse
        for uid, u in self.users.items():
            n_follows = min(len(user_ids) - 1, u["following"])
            if n_follows <= 0:
                continue
            targets = random.sample(user_ids, k=min(n_follows, 40))
            for t in targets:
                if t != uid:
                    self.g.add_edge(uid, t, kind="follows",
                                     ts=u["created_at"] + timedelta(days=random.randint(0, 200)))

    # ---------- fraud injection ----------
    def _gen_fraud_clusters(self, total_fraud_users, n_clusters):
        repo_ids = list(self.repos.keys())
        per_cluster = total_fraud_users // n_clusters
        remaining = total_fraud_users

        cluster_archetypes = [
            "same_minute_signup", "mutual_follow_ring", "fork_farm", "bulk_starrer"
        ]

        uid_counter = 0
        for c in range(n_clusters):
            size = per_cluster if c < n_clusters - 1 else remaining
            remaining -= size
            archetype = cluster_archetypes[c % len(cluster_archetypes)]

            burst_start = NOW - timedelta(days=random.randint(8, 90))
            burst_minutes = random.randint(20, 50)

            member_ids = []
            for k in range(size):
                uid = f"fraud-{c}-{uid_counter}"
                uid_counter += 1
                created_at = burst_start + timedelta(minutes=random.randint(0, burst_minutes)) \
                    if archetype == "same_minute_signup" else \
                    burst_start + timedelta(days=random.randint(0, 20))

                # ~30% of each ring is "sophisticated": a maintained-looking
                # profile (real repos, commits, followers, older account)
                # that only the graph — shared burst timing, mutual
                # follows, co-starring — gives away. Without these, a
                # profile-only classifier could catch every fraud account
                # from raw stats alone, which isn't realistic and hides
                # what the GNN actually contributes.
                sophisticated = random.random() < 0.30

                if sophisticated:
                    followers = max(0, int(np.random.lognormal(1.6, 1.0)))
                    public_repos = max(1, int(np.random.lognormal(1.0, 0.8)))
                    commits = public_repos * max(1, int(np.random.lognormal(2.5, 1.0)))
                    created_at = burst_start - timedelta(days=random.randint(60, 500))
                else:
                    followers = random.choice([0, 0, 0, 1])
                    public_repos = 0 if archetype != "fork_farm" else random.randint(20, 60)
                    commits = 0 if archetype != "fork_farm" else random.randint(0, 2)

                self.users[uid] = {
                    "id": uid,
                    "handle": f"@{'starbot' if archetype=='bulk_starrer' else 'gh-user' if archetype=='mutual_follow_ring' else 'anon-fork' if archetype=='fork_farm' else 'quickstar'}-{4000 + uid_counter}",
                    "created_at": created_at,
                    "followers": followers,
                    "following": 0,
                    "public_repos": public_repos,
                    "public_gists": 0,
                    "commits": commits,
                    "is_fraud": True,
                    "fraud_cluster": c,
                    "archetype": archetype,
                    "sophisticated": sophisticated,
                }
                self.g.add_node(uid, kind="user")
                member_ids.append(uid)

            # Behavior per archetype
            target_repos = random.sample(repo_ids, k=random.randint(2, 6))
            for uid in member_ids:
                u = self.users[uid]
                # Coordinated activity is timed off the CLUSTER's burst
                # window, not the individual account's created_at — a
                # "sophisticated" member's profile is backdated, but it
                # still stars/follows in lockstep with the rest of the
                # ring, which is exactly the tell that only graph timing
                # features (not profile features) can pick up.
                if archetype in ("bulk_starrer", "same_minute_signup"):
                    n_targets = random.randint(20, 45)
                    chosen = random.sample(repo_ids, k=min(n_targets, len(repo_ids)))
                    # heavy overlap with cluster's shared target repos
                    chosen = list(set(chosen) | set(target_repos))
                    burst_ts = burst_start + timedelta(hours=random.randint(0, 6))
                    for rid in chosen:
                        self.g.add_edge(uid, rid, kind="starred", ts=burst_ts + timedelta(minutes=random.randint(0, 90)))
                        self.repos[rid]["fraud_stars"] += 1

                if archetype == "mutual_follow_ring":
                    others = [m for m in member_ids if m != uid]
                    for t in random.sample(others, k=min(len(others), random.randint(5, 15))):
                        self.g.add_edge(uid, t, kind="follows", ts=burst_start)
                    # rings also do a modest star burst together
                    for rid in target_repos:
                        self.g.add_edge(uid, rid, kind="starred", ts=burst_start + timedelta(hours=1))
                        self.repos[rid]["fraud_stars"] += 1

                if archetype == "fork_farm":
                    for rid in random.sample(repo_ids, k=min(max(u["public_repos"], 20), len(repo_ids))):
                        self.g.add_edge(uid, rid, kind="forked", ts=burst_start)
                        self.g.add_edge(uid, rid, kind="starred", ts=burst_start)
                        self.repos[rid]["fraud_stars"] += 1

            self.clusters.append({
                "id": f"cluster-{c}",
                "tag": f"#{c}",
                "archetype": archetype,
                "members": member_ids,
                "target_repos": target_repos,
                "burst_start": burst_start,
            })

    def generate(self):
        self._gen_normal_users(settings.NUM_NORMAL_USERS)
        self._gen_repos(settings.NUM_REPOS)
        self._gen_organic_edges()
        self._gen_fraud_clusters(settings.NUM_FRAUD_USERS, settings.NUM_FRAUD_CLUSTERS)
        return self


def generate_graph():
    return GitHubGraphGenerator().generate()

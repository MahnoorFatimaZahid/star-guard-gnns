import json
import re


def initials_from_handle(handle: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]", " ", handle.replace("@", ""))
    parts = [p for p in clean.split(" ") if p]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def loads(x, default=None):
    if x is None:
        return default
    try:
        return json.loads(x)
    except Exception:
        return default


def row_to_user_card(row):
    tags = loads(row["tags"], [])
    factors = loads(row["factors"], [])
    peers = loads(row["peers"], [])
    return {
        "id": row["id"],
        "handle": row["handle"],
        "initials": initials_from_handle(row["handle"]),
        "meta": f"{row['public_repos']} repos · {row['commits']} commits",
        "score": int(row["score"]),
        "level": row["level"],
        "tags": tags,
        "age": row["age_label"],
        "links": row["links"],
        "why": row["why"],
        "factors": [
            {"label": f["label"], "val": f["val"], "w": f["width"], "c": f["color"]}
            for f in factors
        ],
        "peers": peers,
    }


def row_to_repo_card(row):
    tags = loads(row["tags"], [])
    stars = int(row["stars"])
    return {
        "name": row["name"],
        "url": row["url"],
        "meta": f"{stars:,} stars · {row['flagged_count']} flagged stargazers",
        "score": int(row["score"]),
        "color": row["color"],
        "stars": f"{stars:,}",
        "tags": tags,
        "flagged": f"{row['flagged_count']} flagged stargazers",
        "path": row["sparkline_path"],
    }

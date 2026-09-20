#!/usr/bin/env python3
"""
Run this to test StarGuard against REAL, live GitHub accounts instead of
the synthetic data. See the README section "Testing on real GitHub data"
for the 2-minute token setup.

Usage:
    python scripts/run_real_data_test.py
    python scripts/run_real_data_test.py --repos torvalds/linux facebook/react
    GITHUB_TOKEN=ghp_xxx python scripts/run_real_data_test.py

Output:
    data/real_test_results.csv       - every account checked, both scores
    data/real_test_summary.md        - short plain-English summary
"""
import sys
import os
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.real_data import run_real_test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos", nargs="+", default=None,
                         help="owner/repo pairs to check (default: 5 well-known repos)")
    parser.add_argument("--max-profiles", type=int, default=150,
                         help="max accounts to fetch full profile detail for")
    args = parser.parse_args()

    result = run_real_test(repos=args.repos, max_profile_lookups=args.max_profiles)

    csv_path = os.path.join(settings.DATA_DIR, "real_test_results.csv")
    fieldnames = [
        "handle", "github_url", "has_profile_data", "followers", "following",
        "public_repos", "commits_last_year", "account_age_days", "star_count",
        "co_star_burst_partners", "rule_based_score", "rule_based_reasons",
        "gnn_confidence_experimental", "approximated_fields",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in result["results"]:
            row = dict(row)
            row["rule_based_reasons"] = "; ".join(row["rule_based_reasons"])
            row["approximated_fields"] = "; ".join(row["approximated_fields"])
            writer.writerow(row)

    flagged = [r for r in result["results"] if r["rule_based_score"] >= 50]
    md_path = os.path.join(settings.DATA_DIR, "real_test_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Real GitHub data test — results\n\n")
        f.write(f"- Repos checked: {', '.join(result['repos_checked'])}\n")
        f.write(f"- Unique accounts seen: {result['total_unique_accounts']}\n")
        f.write(f"- Accounts with full profile lookup: {result['profiles_enriched']}\n")
        f.write(f"- Used a GITHUB_TOKEN: {'yes' if result['used_token'] else 'no (sample was shrunk to stay under rate limits)'}\n\n")
        f.write(f"## Flagged by the rule-based check (score >= 50): {len(flagged)}\n\n")
        for r in flagged[:30]:
            f.write(f"- **{r['handle']}** — score {r['rule_based_score']}/100 "
                    f"(GNN confidence: {r['gnn_confidence_experimental']})\n")
            f.write(f"  - why: {'; '.join(r['rule_based_reasons']) or 'no specific reason met'}\n")
        f.write("\n_Full detail for every account checked is in real_test_results.csv._\n")
        f.write("\n**Reminder:** the GNN confidence number is experimental here — the model was\n"
                "trained only on synthetic data and has never seen a labeled real account, so\n"
                "treat it as \"does the pattern transfer at all\", not a validated score.\n")

    print(f"\nDone. Wrote:\n  {csv_path}\n  {md_path}")
    print(f"Flagged {len(flagged)} of {result['total_unique_accounts']} accounts by the rule-based check.")


if __name__ == "__main__":
    main()

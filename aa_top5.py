# Data provided by Artificial Analysis — https://artificialanalysis.ai/

import os
import sys
import requests


API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"


def run_track(models, score_key, track_label, score_col_label):
    candidates = []
    for model in models:
        score = (model.get("evaluations") or {}).get(score_key)
        price = (model.get("pricing") or {}).get("price_1m_blended_3_to_1")
        if score is None or price is None or price == 0:
            continue
        candidates.append({
            "model": model.get("name", ""),
            "creator": (model.get("model_creator") or {}).get("name", ""),
            "score": score,
            "price": price,
        })

    if not candidates:
        print(f"Error: no models with populated {score_key}. Cannot run {track_label} track.")
        sys.exit(1)

    max_score = max(c["score"] for c in candidates)
    threshold = max_score * 0.80
    print(f"=== {track_label} Track ===")
    print(f"{score_col_label} threshold (80% of max {max_score:.1f}): {threshold:.1f}\n")

    scored = [
        {**c, "value": c["score"] / c["price"]}
        for c in candidates
        if c["score"] >= threshold
    ]

    top5 = sorted(scored, key=lambda x: x["value"], reverse=True)[:5]

    header = f"{'Rank':<5} {'Model':<35} {'Creator':<20} {score_col_label:>12} {'Price/1M':>10} {'Value Score':>12}"
    print(header)
    print("-" * len(header))
    for i, m in enumerate(top5, 1):
        print(
            f"{i:<5} {m['model']:<35} {m['creator']:<20} "
            f"{m['score']:>12.1f} {m['price']:>10.4f} {m['value']:>12.1f}"
        )
    print()


def main():
    api_key = os.environ.get("AA_KEY")
    if not api_key:
        print("Error: AA_KEY environment variable is not set.")
        sys.exit(1)

    response = requests.get(API_URL, headers={"x-api-key": api_key})
    if not response.ok:
        print(f"Error: API request failed with status {response.status_code}.")
        sys.exit(1)

    models = response.json()["data"]

    run_track(models, "artificial_analysis_intelligence_index", "Agentic", "Intel. Index")
    run_track(models, "artificial_analysis_coding_index", "Coding", "Coding Index")


if __name__ == "__main__":
    main()

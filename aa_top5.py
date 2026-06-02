# Data provided by Artificial Analysis — https://artificialanalysis.ai/

import os
import sys
import argparse


API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
DATA_CREDIT = "Data provided by Artificial Analysis — https://artificialanalysis.ai/"
EFFORT_THRESHOLDS = {
    "low": 0.70,
    "medium": 0.80,
    "high": 0.90,
    "xhigh": 0.99,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find the cheapest good-enough LLMs from Artificial Analysis data."
    )
    parser.add_argument(
        "--effort",
        choices=EFFORT_THRESHOLDS.keys(),
        default="medium",
        help="Task effort level used for the minimum score threshold. Default: medium.",
    )
    parser.add_argument(
        "--provider",
        help="Filter models by provider/creator name. Case-insensitive substring match.",
    )
    return parser.parse_args()


def run_track(
    models,
    score_key,
    track_label,
    score_col_label,
    effort,
    threshold_ratio,
    provider_filter=None,
):
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
        print(
            f"Error: no models with both populated {score_key} and price. "
            f"Cannot run {track_label} track."
        )
        sys.exit(1)

    max_score = max(c["score"] for c in candidates)
    threshold = max_score * threshold_ratio
    threshold_percent = int(threshold_ratio * 100)

    print(f"=== {track_label} Track ===")
    print(f"Selected track: {track_label}")
    print(f"Selected effort: {effort}")
    if provider_filter:
        print(f"Provider filter: {provider_filter}")
    print(f"Threshold percentage: {threshold_percent}%")
    print(f"Maximum {score_col_label}: {max_score:.1f}")
    print(f"Minimum {score_col_label} threshold: {threshold:.1f}\n")

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
    args = parse_args()
    threshold_ratio = EFFORT_THRESHOLDS[args.effort]

    api_key = os.environ.get("AA_KEY")
    if not api_key:
        print("Error: AA_KEY environment variable is not set.")
        sys.exit(1)

    import requests

    response = requests.get(API_URL, headers={"x-api-key": api_key})
    if not response.ok:
        print(f"Error: API request failed with status {response.status_code}.")
        sys.exit(1)

    models = response.json()["data"]
    if args.provider:
        provider_filter = args.provider.strip().lower()
        models = [
            model
            for model in models
            if provider_filter
            and provider_filter in (model.get("model_creator") or {}).get("name", "").lower()
        ]
        if not models:
            print(
                f"Error: no models found for provider filter '{args.provider}'.",
                file=sys.stderr,
            )
            sys.exit(1)

    run_track(
        models,
        "artificial_analysis_intelligence_index",
        "Agentic",
        "Intel. Index",
        args.effort,
        threshold_ratio,
        args.provider.strip() if args.provider else None,
    )
    run_track(
        models,
        "artificial_analysis_coding_index",
        "Coding",
        "Coding Index",
        args.effort,
        threshold_ratio,
        args.provider.strip() if args.provider else None,
    )
    print(DATA_CREDIT)


if __name__ == "__main__":
    main()

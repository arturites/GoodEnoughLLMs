# Data provided by Artificial Analysis - https://artificialanalysis.ai/

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
DATA_CREDIT = "Data provided by Artificial Analysis - https://artificialanalysis.ai/"
EFFORT_THRESHOLDS = {
    "low": 0.70,
    "medium": 0.80,
    "high": 0.90,
    "xhigh": 0.99,
}
ENV_FILE_NAME = ".env"
CONFIG_DIR_NAME = "goodenoughllms"


class AppError(Exception):
    """Recoverable application error."""


def global_env_file_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / CONFIG_DIR_NAME / ENV_FILE_NAME


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find the cheapest good-enough LLMs from Artificial Analysis data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 aa_top5.py\n"
            "  python3 aa_top5.py --effort high\n"
            "  python3 aa_top5.py --provider OpenAI\n\n"
            "AA_KEY is read from the process environment first, then from "
            "$XDG_CONFIG_HOME/goodenoughllms/.env (default: ~/.config/goodenoughllms/.env)."
        ),
    )
    parser.add_argument(
        "--effort",
        choices=list(EFFORT_THRESHOLDS),
        default="medium",
        help="Task effort level used for the minimum score threshold. Default: medium.",
    )
    parser.add_argument(
        "--provider",
        help="Filter models by provider/creator name. Case-insensitive substring match.",
    )
    return parser.parse_args(argv)


def read_api_key_from_env_file(env_file: Path) -> str | None:
    try:
        content = env_file.read_text(encoding="utf-8")
    except OSError:
        return None

    assignment_re = re.compile(r"^(?:export\s+)?AA_KEY=(?P<value>.*)$")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = assignment_re.match(line)
        if not match:
            continue

        value = match.group("value").strip()
        if not value:
            return ""

        value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        return value

    return None


def load_api_key() -> str | None:
    api_key = os.environ.get("AA_KEY", "").strip()
    if api_key:
        return api_key

    api_key = read_api_key_from_env_file(global_env_file_path())
    if api_key:
        return api_key

    return None


def fetch_models(api_key: str) -> list[dict[str, object]]:
    request = urllib.request.Request(API_URL, headers={"x-api-key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace").strip()
        detail = ""
        if body:
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                for key in ("error", "message", "detail", "description"):
                    if parsed.get(key):
                        detail = str(parsed[key])
                        break
            if not detail:
                detail = body
            if len(detail) > 400:
                detail = detail[:397] + "..."
        if detail:
            raise AppError(f"Error: API request failed with HTTP {exc.code}: {detail}") from exc
        raise AppError(f"Error: API request failed with HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise AppError(f"Error: API request failed: {exc.reason}.") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AppError(f"Error: API response was not valid JSON: {exc.msg}.") from exc

    models = data.get("data")
    if not isinstance(models, list):
        raise AppError("Error: API response did not contain a top-level 'data' list.")

    return models


def normalize_provider_filter(provider: str | None) -> str | None:
    if provider is None:
        return None

    normalized = provider.strip()
    if not normalized:
        raise AppError("Error: --provider cannot be empty.")

    return normalized


def filter_models_by_provider(models: list[dict[str, object]], provider_filter: str | None) -> list[dict[str, object]]:
    if provider_filter is None:
        return models

    provider_filter_lower = provider_filter.lower()
    filtered_models = []
    for model in models:
        creator_data = model.get("model_creator")
        creator = creator_data.get("name", "") if isinstance(creator_data, dict) else ""
        if provider_filter_lower in str(creator).lower():
            filtered_models.append(model)

    return filtered_models


def onboarding_message(env_file: Path) -> str:
    return (
        "Error: AA_KEY is not set.\n\n"
        "Onboarding:\n"
        f"- Add your Artificial Analysis API key as AA_KEY in your process environment, or in {env_file}.\n"
        "- Example line:\n"
        "  AA_KEY=your_api_key_here\n"
        "- Do not commit secrets to the repository.\n"
        "- Then rerun the command. No API call was made."
    )


def run_track(
    models: list[dict[str, object]],
    score_key: str,
    track_label: str,
    score_col_label: str,
    effort: str,
    threshold_ratio: float,
    provider_filter: str | None = None,
) -> bool:
    candidates = []
    for model in models:
        evaluations_data = model.get("evaluations")
        pricing_data = model.get("pricing")
        creator_data = model.get("model_creator")
        evaluations = evaluations_data if isinstance(evaluations_data, dict) else {}
        pricing = pricing_data if isinstance(pricing_data, dict) else {}

        try:
            score = float(evaluations.get(score_key))
            price = float(pricing.get("price_1m_blended_3_to_1"))
        except (TypeError, ValueError):
            continue

        if price <= 0:
            continue

        candidates.append(
            {
                "model": model.get("name", ""),
                "creator": creator_data.get("name", "") if isinstance(creator_data, dict) else "",
                "score": score,
                "price": price,
            }
        )

    if not candidates:
        print(
            f"Error: no models with both populated {score_key} and price. "
            f"Cannot run {track_label} track.",
            file=sys.stderr,
        )
        return False

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
        {**candidate, "value": candidate["score"] / candidate["price"]}
        for candidate in candidates
        if candidate["score"] >= threshold
    ]

    top5 = sorted(scored, key=lambda item: item["value"], reverse=True)[:5]

    header = (
        f"{'Rank':<5} {'Model':<35} {'Creator':<20} "
        f"{score_col_label:>12} {'Price/1M':>10} {'Value Score':>12}"
    )
    print(header)
    print("-" * len(header))
    for index, model in enumerate(top5, 1):
        print(
            f"{index:<5} {model['model']:<35} {model['creator']:<20} "
            f"{model['score']:>12.1f} {model['price']:>10.4f} {model['value']:>12.1f}"
        )
    print()

    return True


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        effort = args.effort
        threshold_ratio = EFFORT_THRESHOLDS[effort]
        provider_filter = normalize_provider_filter(args.provider)

        api_key = load_api_key()
        if not api_key:
            print(onboarding_message(global_env_file_path()), file=sys.stderr)
            return 1

        models = fetch_models(api_key)
        models = filter_models_by_provider(models, provider_filter)
        if provider_filter and not models:
            print(
                f"Error: no models found for provider filter '{provider_filter}'.",
                file=sys.stderr,
            )
            return 1

        if not run_track(
            models,
            "artificial_analysis_intelligence_index",
            "Agentic",
            "Intel. Index",
            effort,
            threshold_ratio,
            provider_filter,
        ):
            return 1

        if not run_track(
            models,
            "artificial_analysis_coding_index",
            "Coding",
            "Coding Index",
            effort,
            threshold_ratio,
            provider_filter,
        ):
            return 1

        print(DATA_CREDIT)
        return 0
    except AppError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# Data provided by Artificial Analysis — https://artificialanalysis.ai/

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
DATA_CREDIT = "Data provided by Artificial Analysis — https://artificialanalysis.ai/"
QUALITY_THRESHOLDS = {
    "basic": 0.60,
    "good": 0.80,
    "high": 0.90,
    "max": 0.99,
}


class AppError(Exception):
    """Recoverable application error."""


def skill_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "SKILL.md").is_file():
            return candidate
    raise RuntimeError("Could not locate the GoodEnoughLLMs skill root.")


def skill_env_file_path() -> Path:
    return skill_root() / ".env"


def skill_env_example_path() -> Path:
    return skill_root() / ".env.example"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find the cheapest good-enough LLMs from Artificial Analysis data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 scripts/aa_top5.py\n"
            "  python3 scripts/aa_top5.py --quality basic\n"
            "  python3 scripts/aa_top5.py --quality good\n"
            "  python3 scripts/aa_top5.py --quality high\n"
            "  python3 scripts/aa_top5.py --quality max\n"
            "  python3 scripts/aa_top5.py --provider OpenAI\n\n"
            "AA_KEY is read from the process environment first, then from the "
            "skill-local .env file next to SKILL.md."
        ),
    )
    parser.add_argument(
        "--quality",
        choices=list(QUALITY_THRESHOLDS),
        default="good",
        help=(
            "Minimum quality level relative to the best available model in each track. "
            "basic=60%%, good=80%%, high=90%%, max=99%%. Default: good."
        ),
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


def load_api_key(env: dict[str, str] | os._Environ[str] | None = None, env_file: Path | None = None) -> str | None:
    active_env = os.environ if env is None else env
    candidate_file = skill_env_file_path() if env_file is None else env_file

    api_key = active_env.get("AA_KEY", "").strip()
    if api_key:
        return api_key

    api_key = read_api_key_from_env_file(candidate_file)
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
        "GoodEnoughLLMs needs an Artificial Analysis API key.\n\n"
        "No AA_KEY was found in the environment or skill-local .env file.\n\n"
        "Expected env file:\n"
        f"  {env_file}\n\n"
        "Create it with:\n"
        "  cp .env.example .env\n\n"
        "Then edit `.env` and replace:\n\n"
        "  AA_KEY=your_artificial_analysis_api_key_here\n\n"
        "with your real Artificial Analysis API key.\n\n"
        "The skill did not call the Artificial Analysis API."
    )


def render_session_header(quality: str) -> None:
    print("GoodEnoughLLMs")
    print(f"Selected quality: {quality}")
    print()


def format_price(price: float) -> str:
    price_text = f"{price:.4f}".rstrip("0").rstrip(".")
    return f"${price_text}"


def run_track(
    models: list[dict[str, object]],
    score_key: str,
    track_label: str,
    score_col_label: str,
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

    max_score = max(candidate["score"] for candidate in candidates)
    threshold = max_score * threshold_ratio
    threshold_percent = int(threshold_ratio * 100)

    print(f"{track_label} Track")
    print(f"Quality threshold: {threshold_percent}%")
    if provider_filter:
        print(f"Provider filter: {provider_filter}")
    print(f"Maximum {score_col_label}: {max_score:.1f}")
    print(f"Minimum {score_col_label} threshold: {threshold:.1f}\n")

    scored = [
        {**candidate, "value": candidate["score"] / candidate["price"]}
        for candidate in candidates
        if candidate["score"] >= threshold
    ]

    top5 = sorted(scored, key=lambda item: item["value"], reverse=True)[:5]

    for index, model in enumerate(top5, 1):
        print(f"{index}. {model['model']}")
        print(f"   Creator: {model['creator']}")
        print(f"   {score_col_label}: {model['score']:.1f}")
        print(f"   Price/1M: {format_price(model['price'])}")
        print(f"   Value Score: {model['value']:.1f}")
        print()

    return True


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        quality = args.quality
        threshold_ratio = QUALITY_THRESHOLDS[quality]
        provider_filter = normalize_provider_filter(args.provider)

        env_file = skill_env_file_path()
        api_key = load_api_key(env_file=env_file)
        if not api_key:
            print(onboarding_message(env_file), file=sys.stderr)
            return 1

        models = fetch_models(api_key)
        models = filter_models_by_provider(models, provider_filter)
        if provider_filter and not models:
            print(
                f"Error: no models found for provider filter '{provider_filter}'.",
                file=sys.stderr,
            )
            return 1

        render_session_header(quality)

        if not run_track(
            models,
            "artificial_analysis_intelligence_index",
            "Agentic",
            "Intel. Index",
            threshold_ratio,
            provider_filter,
        ):
            return 1

        if not run_track(
            models,
            "artificial_analysis_coding_index",
            "Coding",
            "Coding Index",
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

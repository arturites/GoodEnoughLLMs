#!/usr/bin/env python3
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


APP_NAME = "GoodEnoughLLMs"
VERSION = "1.0.0"
API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
DATA_CREDIT = "Data provided by Artificial Analysis - https://artificialanalysis.ai/"
TOP_N = 5
QUALITY_THRESHOLDS = {
    "basic": 0.60,
    "good": 0.80,
    "high": 0.90,
    "max": 0.99,
}

EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_API = 4
EXIT_NO_RESULTS = 5


class AppError(Exception):
    """Recoverable application error with a stable exit code."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class CliArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that can emit JSON usage errors when requested."""

    def __init__(self, *args: object, json_errors: bool = False, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.json_errors = json_errors

    def error(self, message: str) -> None:
        if self.json_errors:
            print(json.dumps({"error": f"CLI usage error: {message}", "exit_code": EXIT_USAGE}, indent=2), file=sys.stderr)
            raise SystemExit(EXIT_USAGE)
        super().error(message)


def project_root() -> Path:
    return Path(__file__).resolve().parent


def env_file_path() -> Path:
    return project_root() / ".env"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    active_argv = sys.argv[1:] if argv is None else argv
    parser = CliArgumentParser(
        json_errors="--json" in active_argv,
        prog="goodenoughllms.py",
        description="Find the cheapest good-enough LLMs from Artificial Analysis data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 goodenoughllms.py\n"
            "  python3 goodenoughllms.py --quality basic\n"
            "  python3 goodenoughllms.py --quality high --provider OpenAI\n"
            "  python3 goodenoughllms.py --json\n\n"
            "AA_KEY is read from the process environment first, then from the\n"
            ".env file next to goodenoughllms.py."
        ),
    )
    parser.add_argument(
        "--quality",
        choices=list(QUALITY_THRESHOLDS),
        default="good",
        help=(
            "Minimum quality threshold relative to the best available model in each track. "
            "basic=60%%, good=80%%, high=90%%, max=99%%. Default: good."
        ),
    )
    parser.add_argument(
        "--provider",
        help="Filter models by model_creator.name. Case-insensitive substring match.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of human-readable tables.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
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
    candidate_file = env_file_path() if env_file is None else env_file

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
            raise AppError(f"API request failed with HTTP {exc.code}: {detail}", EXIT_API) from exc
        raise AppError(f"API request failed with HTTP {exc.code}.", EXIT_API) from exc
    except urllib.error.URLError as exc:
        raise AppError(f"API request failed: {exc.reason}.", EXIT_API) from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AppError(f"API response was not valid JSON: {exc.msg}.", EXIT_API) from exc

    models = data.get("data")
    if not isinstance(models, list):
        raise AppError("API response did not contain a top-level 'data' list.", EXIT_API)

    return models


def normalize_provider_filter(provider: str | None) -> str | None:
    if provider is None:
        return None

    normalized = provider.strip()
    if not normalized:
        raise AppError("--provider cannot be empty.", EXIT_USAGE)

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
        f"{APP_NAME} needs an Artificial Analysis API key.\n\n"
        "No AA_KEY was found in the environment or in the local .env file.\n\n"
        "Set AA_KEY in your shell, or create:\n"
        f"  {env_file}\n\n"
        "with:\n"
        "  AA_KEY=your_artificial_analysis_api_key_here\n\n"
        "You can start from:\n"
        "  cp .env.example .env\n\n"
        "The CLI did not call the Artificial Analysis API."
    )


def format_price(price: float) -> str:
    price_text = f"{price:.4f}".rstrip("0").rstrip(".")
    return f"${price_text}"


def render_table(headers: list[str], rows: list[list[str]], alignments: list[str] | None = None) -> None:
    if alignments is None:
        alignments = ["left"] * len(headers)
    if len(headers) != len(alignments):
        raise ValueError("headers and alignments must have the same length.")

    normalized_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in normalized_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render_cell(text: str, width: int, alignment: str) -> str:
        if alignment == "right":
            return text.rjust(width)
        return text.ljust(width)

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    print(border)
    print(
        "|"
        + "|".join(
            f" {render_cell(headers[index], widths[index], 'left')} "
            for index in range(len(headers))
        )
        + "|"
    )
    print(border)
    for row in normalized_rows:
        print(
            "|"
            + "|".join(
                f" {render_cell(row[index], widths[index], alignments[index])} "
                for index in range(len(headers))
            )
            + "|"
        )
    print(border)


def build_track_result(
    models: list[dict[str, object]],
    score_key: str,
    track_name: str,
    score_label: str,
    threshold_ratio: float,
) -> dict[str, object]:
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
                "name": str(model.get("name", "")),
                "creator": creator_data.get("name", "") if isinstance(creator_data, dict) else "",
                "score": score,
                "price_1m": price,
            }
        )

    if not candidates:
        raise AppError(
            f"No models contained both {score_key} and price data for the {track_name} track.",
            EXIT_NO_RESULTS,
        )

    max_score = max(candidate["score"] for candidate in candidates)
    threshold = max_score * threshold_ratio
    scored = []
    for candidate in candidates:
        if candidate["score"] < threshold:
            continue
        scored.append({**candidate, "value_score": candidate["score"] / candidate["price_1m"]})

    if not scored:
        raise AppError(
            f"No models met the selected quality threshold for the {track_name} track.",
            EXIT_NO_RESULTS,
        )

    top_models = sorted(
        scored,
        key=lambda item: (-item["value_score"], -item["score"], item["price_1m"], item["name"]),
    )[:TOP_N]

    models_output = []
    for index, model in enumerate(top_models, 1):
        models_output.append(
            {
                "rank": index,
                "name": model["name"],
                "creator": model["creator"],
                "score": model["score"],
                "price_1m": model["price_1m"],
                "value_score": model["value_score"],
            }
        )

    return {
        "name": track_name,
        "score_key": score_key,
        "score_label": score_label,
        "quality_threshold_ratio": threshold_ratio,
        "quality_threshold_percent": int(threshold_ratio * 100),
        "max_score": max_score,
        "min_score_threshold": threshold,
        "models": models_output,
    }


def build_result(quality: str, provider_filter: str | None) -> dict[str, object]:
    threshold_ratio = QUALITY_THRESHOLDS[quality]
    env_file = env_file_path()
    api_key = load_api_key(env_file=env_file)
    if not api_key:
        raise AppError(onboarding_message(env_file), EXIT_CONFIG)

    models = fetch_models(api_key)
    models = filter_models_by_provider(models, provider_filter)
    if provider_filter and not models:
        raise AppError(f"No models found for provider filter '{provider_filter}'.", EXIT_NO_RESULTS)

    tracks = [
        build_track_result(
            models,
            "artificial_analysis_intelligence_index",
            "Agentic",
            "Intel. Index",
            threshold_ratio,
        ),
        build_track_result(
            models,
            "artificial_analysis_coding_index",
            "Coding",
            "Coding Index",
            threshold_ratio,
        ),
    ]

    return {
        "tool": APP_NAME,
        "version": VERSION,
        "selected_quality": quality,
        "quality_threshold_ratio": threshold_ratio,
        "quality_threshold_percent": int(threshold_ratio * 100),
        "provider_filter": provider_filter,
        "tracks": tracks,
        "data_credit": DATA_CREDIT,
    }


def render_human_output(result: dict[str, object]) -> None:
    print(APP_NAME)
    print(f"Selected quality: {result['selected_quality']}")
    provider_filter = result.get("provider_filter")
    if provider_filter:
        print(f"Provider filter: {provider_filter}")
    print()

    tracks = result.get("tracks", [])
    for track in tracks:
        if not isinstance(track, dict):
            continue

        print(f"{track['name']} Track")
        print(f"Quality threshold: {track['quality_threshold_percent']}%")
        print(f"Maximum {track['score_label']}: {track['max_score']:.1f}")
        print(f"Minimum {track['score_label']} threshold: {track['min_score_threshold']:.1f}")
        print()

        rows = []
        for model in track.get("models", []):
            rows.append(
                [
                    str(model["rank"]),
                    str(model["name"]),
                    str(model["creator"]),
                    f"{model['score']:.1f}",
                    format_price(model["price_1m"]),
                    f"{model['value_score']:.1f}",
                ]
            )

        render_table(
            ["#", "Model", "Creator", str(track["score_label"]), "Price/1M", "Value Score"],
            rows,
            ["right", "left", "left", "right", "right", "right"],
        )
        print()

    print(DATA_CREDIT)


def render_json_output(result: dict[str, object]) -> None:
    print(json.dumps(result, indent=2))


def emit_error(message: str, exit_code: int, json_output: bool) -> None:
    if json_output:
        print(json.dumps({"error": message, "exit_code": exit_code}, indent=2), file=sys.stderr)
        return

    print(f"Error: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    json_output = False
    try:
        args = parse_args(argv)
        json_output = args.json
        provider_filter = normalize_provider_filter(args.provider)
        result = build_result(args.quality, provider_filter)
        if json_output:
            render_json_output(result)
        else:
            render_human_output(result)
        return EXIT_OK
    except AppError as exc:
        emit_error(str(exc), exc.exit_code, json_output)
        return exc.exit_code
    except Exception as exc:
        emit_error(f"Unexpected error: {exc}", EXIT_INTERNAL, json_output)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())

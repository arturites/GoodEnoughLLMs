#!/usr/bin/env python3
# Data provided by Artificial Analysis - https://artificialanalysis.ai/

from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

import requests


APP_NAME = "GoodEnoughLLMs"
VERSION = "2.1.0"
CONFIG_DIR_NAME = ".goodenoughllms"
ENV_FILE_NAME = ".env"
API_KEY_PLACEHOLDER = "your_artificial_analysis_api_key_here"
DEFAULT_ENV_CONTENT = "# GoodEnoughLLMs API key\nAA_KEY=\n"
API_URL = "https://artificialanalysis.ai/api/v2/language/models/free"
DATA_CREDIT = "Data provided by Artificial Analysis - https://artificialanalysis.ai/"
TOP_N = 5
QUALITY_THRESHOLDS = {
    "basic": 0.60,
    "good": 0.80,
    "high": 0.90,
    "max": 0.99,
}
TRACK_CONFIGS = (
    {
        "name": "Intelligence",
        "score_key": "artificial_analysis_intelligence_index",
        "score_label": "Intelligence Index",
        "cost_label": "Cost/Task",
        "value_method": "intelligence_index_cost_per_task",
        "value_formula": (
            "score / artificial_analysis_intelligence_index_cost.cost_per_task.total_cost"
        ),
        "value_description": "Index / reported Intelligence cost per benchmark task",
        "effective_cost_type": "reported",
        "effective_cost_unit": "USD per benchmark task",
        "value_unit": "index points per USD of average benchmark-task cost",
    },
    {
        "name": "Coding",
        "score_key": "artificial_analysis_coding_index",
        "score_label": "Coding Index",
        "cost_label": "Estimated Coding Cost/1M",
        "value_method": "coding_proxy_35_cache_35_input_30_output",
        "value_formula": (
            "score / (0.35 * cache_hit_price_1m + 0.35 * input_price_1m "
            "+ 0.30 * output_price_1m)"
        ),
        "value_description": "Index / estimated Coding cost (35% cache, 35% input, 30% output)",
        "effective_cost_type": "estimated",
        "effective_cost_unit": "USD per 1M weighted tokens",
        "value_unit": "index points per blended USD/1M tokens",
    },
    {
        "name": "Agentic",
        "score_key": "artificial_analysis_agentic_index",
        "score_label": "Agentic Index",
        "cost_label": "Estimated Agentic Cost/1M",
        "value_method": "agentic_proxy_70_cache_20_input_10_output",
        "value_formula": (
            "score / (0.70 * cache_hit_price_1m + 0.20 * input_price_1m "
            "+ 0.10 * output_price_1m)"
        ),
        "value_description": "Index / estimated Agentic cost (70% cache, 20% input, 10% output)",
        "effective_cost_type": "estimated",
        "effective_cost_unit": "USD per 1M weighted tokens",
        "value_unit": "index points per blended USD/1M tokens",
    },
)

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


def user_config_directory(home: Path | None = None) -> Path:
    base_directory = Path.home() if home is None else home
    return base_directory / CONFIG_DIR_NAME


def env_file_path() -> Path:
    return user_config_directory() / ENV_FILE_NAME


def legacy_env_file_path() -> Path:
    return project_root() / ENV_FILE_NAME


def ensure_user_env_file(env_file: Path) -> None:
    try:
        env_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if env_file.exists():
            return

        file_descriptor = os.open(
            env_file,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(DEFAULT_ENV_CONTENT)
    except FileExistsError:
        return
    except OSError as exc:
        raise AppError(
            f"Could not create the configuration file {env_file}: {exc}",
            EXIT_CONFIG,
        ) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    active_argv = sys.argv[1:] if argv is None else argv
    program_name = Path(sys.argv[0]).name or "gelm"
    parser = CliArgumentParser(
        json_errors="--json" in active_argv,
        prog=program_name,
        description="Find the best-value good-enough LLMs from Artificial Analysis data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  gelm\n"
            "  gelm --quality basic\n"
            "  gelm --quality high --provider OpenAI\n"
            "  gelm --json\n\n"
            "AA_KEY is read from the process environment first, then from\n"
            "~/.goodenoughllms/.env. In an interactive terminal, gelm asks\n"
            "for a missing key and stores it in that file."
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


def usable_api_key(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized or normalized == API_KEY_PLACEHOLDER:
        return None
    return normalized


def load_api_key(
    env: dict[str, str] | os._Environ[str] | None = None,
    env_file: Path | None = None,
    legacy_env_file: Path | None = None,
) -> str | None:
    active_env = os.environ if env is None else env
    candidate_file = env_file_path() if env_file is None else env_file

    api_key = usable_api_key(active_env.get("AA_KEY"))
    if api_key:
        return api_key

    files_to_check = [candidate_file]
    fallback_file = legacy_env_file_path() if legacy_env_file is None else legacy_env_file
    if fallback_file != candidate_file:
        files_to_check.append(fallback_file)

    for file_path in files_to_check:
        api_key = usable_api_key(read_api_key_from_env_file(file_path))
        if api_key:
            return api_key

    return None


def write_api_key_to_env_file(env_file: Path, api_key: str) -> None:
    normalized = usable_api_key(api_key)
    if normalized is None:
        raise AppError("The API key cannot be empty.", EXIT_CONFIG)
    if "\n" in normalized or "\r" in normalized:
        raise AppError("The API key cannot contain line breaks.", EXIT_CONFIG)

    ensure_user_env_file(env_file)
    temporary_path: Path | None = None
    try:
        content = env_file.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        assignment_re = re.compile(r"^\s*(?:export\s+)?AA_KEY=")
        replaced = False
        for index, line in enumerate(lines):
            line_without_newline = line.rstrip("\r\n")
            if assignment_re.match(line_without_newline):
                newline = "\r\n" if line.endswith("\r\n") else "\n"
                lines[index] = f"AA_KEY={normalized}{newline}"
                replaced = True
                break

        if replaced:
            updated_content = "".join(lines)
        else:
            separator = "" if not content or content.endswith(("\n", "\r")) else "\n"
            updated_content = f"{content}{separator}AA_KEY={normalized}\n"

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=env_file.parent,
            prefix=f".{env_file.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(updated_content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, env_file)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise AppError(
            f"Could not save the API key to {env_file}: {exc}",
            EXIT_CONFIG,
        ) from exc


def prompt_for_api_key(env_file: Path) -> str | None:
    if not sys.stdin.isatty():
        return None

    try:
        entered_key = getpass.getpass(
            f"Enter your Artificial Analysis API key (stored in {env_file}): "
        )
    except (EOFError, KeyboardInterrupt, OSError):
        print(file=sys.stderr)
        return None

    api_key = usable_api_key(entered_key)
    if api_key is None:
        return None

    write_api_key_to_env_file(env_file, api_key)
    return api_key


def response_error_detail(response: requests.Response) -> str:
    body = response.text.strip()
    if not body:
        return ""

    try:
        parsed = response.json()
    except ValueError:
        parsed = None

    detail = ""
    if isinstance(parsed, dict):
        for key in ("error", "message", "detail", "description"):
            if parsed.get(key):
                detail = str(parsed[key])
                break
    if not detail:
        detail = body
    if len(detail) > 400:
        detail = detail[:397] + "..."
    return detail


def fetch_models(api_key: str) -> tuple[list[dict[str, object]], object]:
    models: list[dict[str, object]] = []
    page = 1
    expected_total_pages: int | None = None
    intelligence_index_version: object = None

    while True:
        try:
            response = requests.get(
                API_URL,
                headers={"x-api-key": api_key},
                params={"page": page},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise AppError(f"API request failed: {exc}", EXIT_API) from exc

        if not 200 <= response.status_code < 300:
            detail = response_error_detail(response)
            if detail:
                raise AppError(
                    f"API request failed with HTTP {response.status_code}: {detail}",
                    EXIT_API,
                )
            raise AppError(f"API request failed with HTTP {response.status_code}.", EXIT_API)

        try:
            data = response.json()
        except ValueError as exc:
            raise AppError(f"API response was not valid JSON: {exc}.", EXIT_API) from exc

        if not isinstance(data, dict):
            raise AppError("API response was not a JSON object.", EXIT_API)

        page_models = data.get("data")
        if not isinstance(page_models, list):
            raise AppError("API response did not contain a top-level 'data' list.", EXIT_API)
        if not all(isinstance(model, dict) for model in page_models):
            raise AppError("API response 'data' contained an invalid model entry.", EXIT_API)
        models.extend(page_models)

        page_version = data.get("intelligence_index_version")
        if page == 1:
            intelligence_index_version = page_version
        elif page_version != intelligence_index_version:
            raise AppError("API response changed Intelligence Index version between pages.", EXIT_API)

        pagination = data.get("pagination")
        if not isinstance(pagination, dict):
            raise AppError("API response did not contain pagination metadata.", EXIT_API)
        has_more = pagination.get("has_more")
        if not isinstance(has_more, bool):
            raise AppError("API response pagination did not contain a boolean 'has_more'.", EXIT_API)
        response_page = pagination.get("page")
        total_pages = pagination.get("total_pages")
        if isinstance(response_page, bool) or not isinstance(response_page, int) or response_page != page:
            raise AppError("API response pagination returned an unexpected page number.", EXIT_API)
        if isinstance(total_pages, bool) or not isinstance(total_pages, int) or total_pages < 1:
            raise AppError("API response pagination returned an invalid total page count.", EXIT_API)
        if expected_total_pages is None:
            expected_total_pages = total_pages
        elif total_pages != expected_total_pages:
            raise AppError("API response pagination changed the total page count between pages.", EXIT_API)
        if has_more != (page < total_pages):
            raise AppError("API response pagination metadata was inconsistent.", EXIT_API)
        if not has_more:
            break
        page += 1

    return models, intelligence_index_version


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
        "No usable AA_KEY was found in the environment or in a .env file.\n\n"
        "Set AA_KEY in your shell, or run gelm in an interactive terminal\n"
        "to enter it securely. The key will be stored in:\n"
        f"  {env_file}\n\n"
        "Example file content:\n"
        "  AA_KEY=your_artificial_analysis_api_key_here\n\n"
        "The CLI did not call the Artificial Analysis API."
    )


def resolve_api_key(env_file: Path, *, interactive: bool) -> str:
    api_key = load_api_key(env_file=env_file)
    if api_key:
        return api_key

    if interactive:
        api_key = prompt_for_api_key(env_file)
        if api_key:
            return api_key

    raise AppError(onboarding_message(env_file), EXIT_CONFIG)


def format_price(price: float) -> str:
    price_text = f"{price:.4f}".rstrip("0").rstrip(".")
    return f"${price_text}"


def finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def token_prices_for_model(model: dict[str, object]) -> tuple[dict[str, float], bool] | None:
    pricing_data = model.get("pricing")
    if not isinstance(pricing_data, dict):
        return None

    input_price = finite_number(pricing_data.get("price_1m_input_tokens"))
    output_price = finite_number(pricing_data.get("price_1m_output_tokens"))
    if input_price is None or output_price is None or input_price < 0 or output_price < 0:
        return None

    raw_cache_price = pricing_data.get("price_1m_cache_hit_tokens")
    cache_price_fallback = raw_cache_price is None
    if cache_price_fallback:
        cache_price = input_price
    else:
        cache_price = finite_number(raw_cache_price)
        if cache_price is None or cache_price < 0:
            return None

    return (
        {
            "input_price_1m": input_price,
            "output_price_1m": output_price,
            "cache_hit_price_1m": cache_price,
        },
        cache_price_fallback,
    )


def effective_cost_for_model(model: dict[str, object], value_method: str) -> tuple[float | None, bool]:
    if value_method == "intelligence_index_cost_per_task":
        cost_data = model.get("artificial_analysis_intelligence_index_cost")
        if not isinstance(cost_data, dict):
            return None, False
        cost_per_task_data = cost_data.get("cost_per_task")
        if not isinstance(cost_per_task_data, dict):
            return None, False
        cost = finite_number(cost_per_task_data.get("total_cost"))
        if cost is None or cost <= 0:
            return None, False
        return cost, False

    price_result = token_prices_for_model(model)
    if price_result is None:
        return None, False
    token_prices, cache_price_fallback = price_result
    input_price = token_prices["input_price_1m"]
    output_price = token_prices["output_price_1m"]
    cache_price = token_prices["cache_hit_price_1m"]

    if value_method == "agentic_proxy_70_cache_20_input_10_output":
        cost = 0.70 * cache_price + 0.20 * input_price + 0.10 * output_price
    elif value_method == "coding_proxy_35_cache_35_input_30_output":
        cost = 0.35 * cache_price + 0.35 * input_price + 0.30 * output_price
    else:
        raise ValueError(f"Unknown value method: {value_method}")

    cost = round(cost, 10)
    if not math.isfinite(cost) or cost <= 0:
        return None, cache_price_fallback
    return cost, cache_price_fallback


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


def track_metadata(track_config: dict[str, str], threshold_ratio: float) -> dict[str, object]:
    return {
        "name": track_config["name"],
        "score_key": track_config["score_key"],
        "score_label": track_config["score_label"],
        "cost_label": track_config["cost_label"],
        "value_method": track_config["value_method"],
        "value_formula": track_config["value_formula"],
        "value_description": track_config["value_description"],
        "effective_cost_type": track_config["effective_cost_type"],
        "effective_cost_unit": track_config["effective_cost_unit"],
        "value_unit": track_config["value_unit"],
        "quality_threshold_ratio": threshold_ratio,
        "quality_threshold_percent": int(threshold_ratio * 100),
    }


def build_track_result(
    models: list[dict[str, object]],
    track_config: dict[str, str],
    threshold_ratio: float,
) -> dict[str, object]:
    score_key = track_config["score_key"]
    track_name = track_config["name"]
    candidates = []
    for model in models:
        evaluations_data = model.get("evaluations")
        creator_data = model.get("model_creator")
        evaluations = evaluations_data if isinstance(evaluations_data, dict) else {}
        score = finite_number(evaluations.get(score_key))
        if score is None or score < 0:
            continue

        candidates.append(
            {
                "name": str(model.get("name", "")),
                "creator": creator_data.get("name", "") if isinstance(creator_data, dict) else "",
                "score": score,
                "model": model,
            }
        )

    if not candidates:
        raise AppError(
            f"No models contained a valid {score_key} score for the {track_name} track.",
            EXIT_NO_RESULTS,
        )

    max_score = max(candidate["score"] for candidate in candidates)
    if max_score <= 0:
        raise AppError(f"The maximum score for the {track_name} track was not positive.", EXIT_NO_RESULTS)
    threshold = max_score * threshold_ratio
    scored = []
    for candidate in candidates:
        if candidate["score"] < threshold:
            continue
        effective_cost, cache_price_fallback = effective_cost_for_model(
            candidate["model"],
            track_config["value_method"],
        )
        if effective_cost is None:
            continue
        token_prices = {}
        if track_config["value_method"] != "intelligence_index_cost_per_task":
            price_result = token_prices_for_model(candidate["model"])
            if price_result is None:
                continue
            token_prices, cache_price_fallback = price_result
        value_score = candidate["score"] / effective_cost
        if not math.isfinite(value_score):
            continue
        scored.append(
            {
                **candidate,
                "effective_cost": effective_cost,
                "value_score": value_score,
                "cache_price_fallback": cache_price_fallback,
                "token_prices": token_prices,
            }
        )

    if not scored:
        raise AppError(
            f"No models met the selected quality threshold with usable cost data for the {track_name} track.",
            EXIT_NO_RESULTS,
        )

    top_models = sorted(
        scored,
        key=lambda item: (
            -item["value_score"],
            -item["score"],
            item["effective_cost"],
            item["name"],
        ),
    )[:TOP_N]

    models_output = []
    for index, model in enumerate(top_models, 1):
        models_output.append(
            {
                "rank": index,
                "name": model["name"],
                "creator": model["creator"],
                "score": model["score"],
                **model["token_prices"],
                "effective_cost": model["effective_cost"],
                "value_score": model["value_score"],
                "cache_price_fallback": model["cache_price_fallback"],
            }
        )

    return {
        **track_metadata(track_config, threshold_ratio),
        "status": "ok",
        "max_score": max_score,
        "min_score_threshold": threshold,
        "models": models_output,
    }


def unavailable_track_result(
    track_config: dict[str, str],
    threshold_ratio: float,
    message: str,
) -> dict[str, object]:
    return {
        **track_metadata(track_config, threshold_ratio),
        "status": "unavailable",
        "error": message,
        "max_score": None,
        "min_score_threshold": None,
        "models": [],
    }


def build_result(
    quality: str,
    provider_filter: str | None,
    *,
    interactive: bool = False,
) -> dict[str, object]:
    threshold_ratio = QUALITY_THRESHOLDS[quality]
    env_file = env_file_path()
    ensure_user_env_file(env_file)
    api_key = resolve_api_key(env_file, interactive=interactive)

    models, intelligence_index_version = fetch_models(api_key)
    models = filter_models_by_provider(models, provider_filter)
    if provider_filter and not models:
        raise AppError(f"No models found for provider filter '{provider_filter}'.", EXIT_NO_RESULTS)

    tracks = []
    for track_config in TRACK_CONFIGS:
        try:
            tracks.append(build_track_result(models, track_config, threshold_ratio))
        except AppError as exc:
            if exc.exit_code != EXIT_NO_RESULTS:
                raise
            tracks.append(unavailable_track_result(track_config, threshold_ratio, str(exc)))

    if not any(track.get("status") == "ok" for track in tracks):
        raise AppError("No tracks contained usable model and cost data.", EXIT_NO_RESULTS)

    return {
        "tool": APP_NAME,
        "version": VERSION,
        "intelligence_index_version": intelligence_index_version,
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
    intelligence_index_version = result.get("intelligence_index_version")
    if intelligence_index_version is not None:
        print(f"Intelligence Index version: v{intelligence_index_version}")
    provider_filter = result.get("provider_filter")
    if provider_filter:
        print(f"Provider filter: {provider_filter}")
    print()

    tracks = result.get("tracks", [])
    for track in tracks:
        if not isinstance(track, dict):
            continue

        print(f"{track['name']} Track")
        if track.get("status") != "ok":
            print(f"Unavailable: {track.get('error', 'No usable data.')}")
            print()
            continue
        print(f"Quality threshold: {track['quality_threshold_percent']}%")
        print(f"Maximum {track['score_label']}: {track['max_score']:.1f}")
        print(f"Minimum {track['score_label']} threshold: {track['min_score_threshold']:.1f}")
        print(f"Value basis: {track['value_description']}")
        print()

        rows = []
        show_token_prices = track["value_method"] != "intelligence_index_cost_per_task"
        used_cache_fallback = False
        for model in track.get("models", []):
            cache_price_fallback = bool(model.get("cache_price_fallback"))
            used_cache_fallback = used_cache_fallback or cache_price_fallback
            effective_cost = format_price(model["effective_cost"])
            row = [
                str(model["rank"]),
                str(model["name"]),
                str(model["creator"]),
                f"{model['score']:.1f}",
            ]
            if show_token_prices:
                cache_price = format_price(model["cache_hit_price_1m"])
                if cache_price_fallback:
                    cache_price += "*"
                row.extend(
                    [
                        format_price(model["input_price_1m"]),
                        format_price(model["output_price_1m"]),
                        cache_price,
                    ]
                )
            row.extend([effective_cost, f"{model['value_score']:.1f}"])
            rows.append(row)

        headers = ["#", "Model", "Creator", str(track["score_label"])]
        alignments = ["right", "left", "left", "right"]
        if show_token_prices:
            headers.extend(["Input/1M", "Output/1M", "Cache/1M"])
            alignments.extend(["right", "right", "right"])
        headers.extend([str(track["cost_label"]), "Value Score"])
        alignments.extend(["right", "right"])
        render_table(headers, rows, alignments)
        if used_cache_fallback:
            print("* Cache-Hit price unavailable; input price used for the cache component.")
        print()

    print(DATA_CREDIT)


def render_json_output(result: dict[str, object]) -> None:
    print(json.dumps(result, indent=2, allow_nan=False))


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
        result = build_result(
            args.quality,
            provider_filter,
            interactive=not json_output and sys.stdin.isatty(),
        )
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

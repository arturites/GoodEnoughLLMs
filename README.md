# GoodEnoughLLMs

GoodEnoughLLMs is a small CLI that fetches live Artificial Analysis model data and prints the top 5 best-value models that are still good enough for the selected quality level.

It focuses on value, not on naming a single objectively best model.

GoodEnoughLLMs is an independent third-party project. It is not affiliated with, developed by, sponsored by, endorsed by, or reviewed by Artificial Analysis. Artificial Analysis is used solely as an external data source through its API.

Value Score means price-performance within the selected quality threshold. A model only competes after it clears the chosen threshold for its track. Intelligence, Coding, and Agentic use different cost models, so their Value Scores must not be compared with one another.

**What It Does**

- Fetches every page from the Artificial Analysis free models API.
- Ranks models separately for the Intelligence, Coding, and Agentic tracks.
- Filters to models that meet the chosen quality threshold.
- Calculates Value Score with a cost basis suited to each track.
- Prints human-readable ASCII tables by default.
- Supports `--json` for machine-readable output.

**Installation**

Requirements:

- Python 3.11+
- [`requests`](https://requests.readthedocs.io/)
- Network access to Artificial Analysis
- An Artificial Analysis API key

Install the runtime dependency in your active Python environment:

```bash
python3 -m pip install requests
```

No packaging step is required. Run the root script directly:

```bash
python3 goodenoughllms.py --help
```

**API Key Configuration**

GoodEnoughLLMs looks for `AA_KEY` in this order:

1. Process environment
2. `.env` in the repository root, next to `goodenoughllms.py`

The repository includes `.env.example`:

```text
AA_KEY=your_artificial_analysis_api_key_here
```

Set it in your shell:

```bash
export AA_KEY=your_artificial_analysis_api_key_here
```

Or create a local `.env` file:

```bash
cp .env.example .env
```

Do not commit `.env`.

**Usage**

Show help:

```bash
python3 goodenoughllms.py --help
```

Show version:

```bash
python3 goodenoughllms.py --version
```

Use the default quality level (`good`):

```bash
python3 goodenoughllms.py
```

Choose a quality threshold:

```bash
python3 goodenoughllms.py --quality basic
python3 goodenoughllms.py --quality good
python3 goodenoughllms.py --quality high
python3 goodenoughllms.py --quality max
```

Filter by provider name:

```bash
python3 goodenoughllms.py --provider OpenAI
python3 goodenoughllms.py --provider anthropic
python3 goodenoughllms.py --quality high --provider meta
```

`--provider` matches `model_creator.name` using a case-insensitive substring search.

Get machine-readable output:

```bash
python3 goodenoughllms.py --json
python3 goodenoughllms.py --quality high --provider OpenAI --json
```

Successful `--json` results are written to stdout. Errors are written as JSON to stderr.

The CLI never prompts interactively.

GoodEnoughLLMs 2.0 reports its version as `2.0.0`:

```text
goodenoughllms.py 2.0.0
```

**Quality Levels**

`quality` is a threshold relative to the best valid index score in each track. It is not a reasoning-budget knob. The maximum score and resulting threshold are determined before models without a usable track-specific cost basis are removed from the Value ranking.

- `basic`: 60%
- `good`: 80%
- `high`: 90%
- `max`: 99%

Examples:

- `basic` keeps very cheap models that still clear 60% of the best available score.
- `good` is the default and keeps models at 80% or better.
- `high` is for harder tasks where you want models closer to the top.
- `max` keeps only models very close to the best available score.

**Tracks**

- Intelligence Track: uses `artificial_analysis_intelligence_index`.
- Coding Track: uses `artificial_analysis_coding_index`.
- Agentic Track: uses `artificial_analysis_agentic_index`.

The CLI presents the tracks in that order. If one track has no usable score or cost data, it is marked as unavailable while the other track results are still returned. Exit code `5` is used when none of the tracks can produce a ranking.

**How Value Score Works**

The calculation runs separately for Intelligence, Coding, and Agentic:

1. Find the highest index score in the track.
2. Multiply it by the selected quality threshold.
3. Remove models below that threshold.
4. Calculate the effective cost for every remaining model.
5. Calculate `Value Score = Index Score / Effective Cost`.
6. Sort by Value Score from highest to lowest and show the top five.

The formulas use these short names:

| Short name | Meaning | Unit |
| --- | --- | --- |
| `S_I` | The model's Intelligence Index score | Index points |
| `S_C` | The model's Coding Index score | Index points |
| `S_A` | The model's Agentic Index score | Index points |
| `P_cache` | Price for cached input tokens | USD per 1 million tokens |
| `P_in` | Price for regular input tokens | USD per 1 million tokens |
| `P_out` | Price for generated output tokens | USD per 1 million tokens |
| `K_I` | Average cost for one Intelligence benchmark task | USD per task |

`K_I` comes directly from the API field:

```text
artificial_analysis_intelligence_index_cost.cost_per_task.total_cost
```

The track formulas are:

```text
Intelligence Cost  = K_I
Intelligence Value = S_I / K_I

Estimated Coding Cost  = 0.35 * P_cache + 0.35 * P_in + 0.30 * P_out
Coding Value           = S_C / Estimated Coding Cost

Estimated Agentic Cost = 0.70 * P_cache + 0.20 * P_in + 0.10 * P_out
Agentic Value          = S_A / Estimated Agentic Cost
```

If `P_cache` is unavailable, the input price is used instead. The cost shown in each table is the same cost used in its formula. Value Scores are comparable only within the same track.

**Why These Cost Defaults**

- Intelligence uses the task cost supplied in the API response.
- Agentic assumes that repeated context makes up most of a multi-step workload, so cached input receives the largest weight.
- Coding combines an agent-style workload with a balanced input/output code-generation workload, resulting in 35% cache, 35% input, and 30% output.

The Coding and Agentic weights are project defaults, not external recommendations.

**Price and Data Rules**

- Coding and Agentic tables show `Input/1M`, `Output/1M`, and `Cache/1M` alongside `Estimated Coding Cost/1M` or `Estimated Agentic Cost/1M`. The word `Estimated` makes clear that these are calculated workload assumptions, not API fields. Intelligence shows only the API's `Cost/Task` value.
- If a cache-hit price is missing for Coding or Agentic, the CLI conservatively uses `P_cache = P_in`, marks the fallback in human output, and sets `cache_price_fallback: true` in JSON.
- Cache-write prices are not included because there is no reliable reuse-count assumption.
- Missing, negative, or non-finite scores and required prices exclude a model only from the affected track. A calculated effective cost must be greater than zero.
- Speed and latency are not part of any Value Score.
- Rankings sort by Value Score descending, then index score descending, effective cost ascending, and model name ascending.
- Value Scores are comparable only within the same track. Do not compare Intelligence, Coding, and Agentic Value Scores numerically.

**API Retrieval**

The CLI uses `requests` to call:

```text
https://artificialanalysis.ai/api/v2/language/models/free
```

It follows the response's `pagination.has_more` flag and requests subsequent pages until all model data has been combined. HTTP, network, and invalid-JSON failures use exit code `4`. When `AA_KEY` is missing, the CLI prints onboarding information to stderr, exits with code `3`, and does not call the API.

**JSON Output**

Version 2.0 changes the machine-readable cost representation. The old, generic `price_1m` model field is replaced by `effective_cost`, whose meaning depends on the track.

Each track includes:

- `status`: `ok` or `unavailable`; unavailable tracks also include `error` and an empty `models` list.
- `value_method`: the formula or method used for the track.
- `effective_cost_type`: `reported` for Intelligence or `estimated` for Coding and Agentic.
- `effective_cost_unit`: `USD per benchmark task` for Intelligence or `USD per 1M weighted tokens` for Coding and Agentic.
- `value_unit`: the track-specific interpretation of `value_score`.

Each ranked model includes `effective_cost`, `value_score`, and `cache_price_fallback` in addition to its rank, identity, and index score. Coding and Agentic models also include `input_price_1m`, `output_price_1m`, and `cache_hit_price_1m`; Intelligence models omit those token-price fields because their Value calculation uses `Cost/Task`. The root result includes `intelligence_index_version` from the API response when available, as well as the unchanged source-attribution string in `data_credit`.

**Exit Codes**

- `0`: success
- `1`: unexpected internal error
- `2`: CLI usage error
- `3`: missing `AA_KEY`
- `4`: API, network, or response error
- `5`: no matching or usable model data

**External Data Source and Independence**

Data provided by Artificial Analysis - https://artificialanalysis.ai/
# GoodEnoughLLMs

GoodEnoughLLMs is a small CLI that fetches live Artificial Analysis model data and prints the top 5 cheapest models that are still good enough for the selected quality level.

It focuses on value, not on naming a single objectively best model.

Value Score means price-performance within the selected quality threshold. A model only competes after it clears the chosen threshold for its track.

**What It Does**

- Fetches model data from the Artificial Analysis API.
- Ranks models separately for the Agentic Track and the Coding Track.
- Filters to models that meet the chosen quality threshold.
- Sorts the remaining models by value score: `score / price per 1M tokens`.
- Prints human-readable ASCII tables by default.
- Supports `--json` for machine-readable output.

**Installation**

Requirements:

- Python 3.11+
- Network access to Artificial Analysis
- An Artificial Analysis API key

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

**Quality Levels**

`quality` is a threshold relative to the best available model in each track. It is not a reasoning-budget knob.

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

- Agentic Track: ranked by the Artificial Analysis Intelligence Index.
- Coding Track: ranked by the Artificial Analysis Coding Index.

The CLI always prints both tracks when usable data is available.

**How Value Score Works**

Value Score is not an "overall winner" score for the entire market.

The flow is:

1. Pick a track.
2. Find the best available score in that track.
3. Apply the selected quality threshold.
4. Rank only the models that passed the threshold by `score / price`.

This means the cheapest acceptable model can outrank a stronger but much more expensive model inside the same threshold window.

**Exit Codes**

- `0`: success
- `2`: CLI usage error
- `3`: missing `AA_KEY`
- `4`: API, network, or response error
- `5`: no matching or usable model data

**Data Source**

Data provided by Artificial Analysis - https://artificialanalysis.ai/

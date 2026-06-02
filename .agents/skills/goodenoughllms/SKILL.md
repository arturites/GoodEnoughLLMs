---
name: goodenoughllms
description: Fetches Artificial Analysis model rankings and prints the top 5 cheapest good-enough LLMs for agentic and coding tasks. Use when you need a value-based shortlist with effort and provider filters.
compatibility: Requires Python 3.11+, network access to Artificial Analysis, and an AA_KEY in the process environment or in $XDG_CONFIG_HOME/goodenoughllms/.env.
---

# GoodEnoughLLMs

Use this skill to shortlist models from Artificial Analysis by value score.

## Run

Run the bundled wrapper from the skill directory:

```bash
python3 scripts/goodenoughllms.py
```

Examples:

```bash
python3 scripts/goodenoughllms.py
python3 scripts/goodenoughllms.py --effort high
python3 scripts/goodenoughllms.py --effort xhigh --provider OpenAI
python3 scripts/goodenoughllms.py --provider Anthropic
python3 scripts/goodenoughllms.py --help
```

## Parameters

- `--effort low|medium|high|xhigh` sets the threshold against the best available score for each track. Default: `medium`.
- `--provider <name>` filters models by `model_creator.name` using a case-insensitive substring match.
- `--help` prints usage and examples.

## Key handling

- Check `AA_KEY` in the process environment first.
- If it is missing, read the global user config file at `$XDG_CONFIG_HOME/goodenoughllms/.env` (default `~/.config/goodenoughllms/.env`).
- If the key is still missing, show onboarding, include `AA_KEY=your_api_key_here`, and stop without making an API call.
- Do not use or create a repo-local `.env`.
- Do not commit secrets.

## Output

Preserve the canonical GoodEnoughLLMs behavior:

- Agentic Track
- Coding Track
- Effort-based threshold summary
- Value Score = score / price
- Sorted top 5 per track
- Credit line: `Data provided by Artificial Analysis - https://artificialanalysis.ai/`

## Failure modes

- Missing `AA_KEY`: show onboarding and exit non-zero.
- API error: show a clear error message.
- No models after filtering: show a clear error message that names the provider filter.

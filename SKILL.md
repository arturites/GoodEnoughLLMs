---
name: goodenoughllms
description: Fetches Artificial Analysis model rankings and prints the top 5 cheapest good-enough LLMs for agentic and coding tasks. Use when you need a value-based shortlist with quality and provider filters.
compatibility: Requires Python 3.11+, network access to Artificial Analysis, and an AA_KEY in the process environment or in a skill-local .env file next to SKILL.md.
---

# GoodEnoughLLMs

Use this skill to shortlist models from Artificial Analysis by value score.

Primary invocation is `/goodenoughllms` in a compatible agent. For local debugging only, the repository includes a Python entry point at `scripts/aa_top5.py`.

## Use

Invoke the skill with slash-command parameters:

```text
/goodenoughllms
```

Examples:

```text
/goodenoughllms
/goodenoughllms --quality basic
/goodenoughllms --quality good
/goodenoughllms --quality high
/goodenoughllms --quality max
/goodenoughllms --quality high --provider OpenAI
/goodenoughllms --provider Anthropic
```

Local debugging:

```bash
python3 scripts/aa_top5.py --help
```

## Parameters

- `--quality basic|good|high|max` sets the minimum quality threshold relative to the best available model in each track. Default: `good`.
- `--provider <name>` filters models by `model_creator.name` using a case-insensitive substring match.
- `--help` prints usage and examples.

## Quality levels

`quality` sets the minimum acceptable model quality relative to the best available model in each track. It does not describe reasoning budget or thinking time.

- `basic`: 60% of the best available model in the track. Good for simple tasks, everyday questions, very cheap models, and maximum cost savings.
- `good`: 80% of the best available model in the track. The Pareto sweet spot and the default. "80% of the performance for a fraction of the cost." Good for most users and daily work.
- `high`: 90% of the best available model in the track. Good for demanding tasks, architecture decisions, complex analysis, difficult coding, and higher-requirement agents.
- `max`: 99% of the best available model in the track. Good for critical tasks, difficult agents, and maximum quality. "If only the best models are acceptable."

## Key handling

- Check `AA_KEY` in the process environment first.
- If it is missing, read `.env` from the skill root, directly next to `SKILL.md`.
- The repository includes `.env.example` as the template for `.env`.
- If the key is still missing, show onboarding and stop without making an API call.
- Do not commit `.env`.

## Output

Preserve the canonical GoodEnoughLLMs behavior:

- Selected quality: `basic|good|high|max`
- Agentic Track
- Coding Track
- Quality-based threshold summary
- Value Score = score / price
- Sorted top 5 per track
- Credit line: `Data provided by Artificial Analysis - https://artificialanalysis.ai/`

## Failure modes

- Missing `AA_KEY`: show onboarding and exit non-zero.
- API error: show a clear error message.
- No models after filtering: show a clear error message that names the provider filter.

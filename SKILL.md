---
name: goodenoughllms
description: Fetches Artificial Analysis model rankings and prints the top 5 cheapest good-enough LLMs for agentic and coding tasks. Use when you need a value-based shortlist with effort and provider filters.
compatibility: Requires Python 3.11+, network access to Artificial Analysis, and an AA_KEY in the process environment or in a skill-local .env file next to SKILL.md.
---

# GoodEnoughLLMs

Use this skill to shortlist models from Artificial Analysis by value score.

Primary invocation is `/goodenoughllms` in a compatible agent. For local debugging only, the repository includes a Python entry point at `scripts/goodenoughllms.py`.

## Use

Invoke the skill with slash-command parameters:

```text
/goodenoughllms
```

Examples:

```text
/goodenoughllms
/goodenoughllms --effort high
/goodenoughllms --effort xhigh --provider OpenAI
/goodenoughllms --provider Anthropic
```

Local debugging:

```bash
python3 scripts/goodenoughllms.py --help
```

## Parameters

- `--effort low|medium|high|xhigh` sets the threshold against the best available score for each track. Default: `medium`.
- `--provider <name>` filters models by `model_creator.name` using a case-insensitive substring match.
- `--help` prints usage and examples.

## Key handling

- Check `AA_KEY` in the process environment first.
- If it is missing, read `.env` from the skill root, directly next to `SKILL.md`.
- The repository includes `.env.example` as the template for `.env`.
- If the key is still missing, show onboarding and stop without making an API call.
- Do not commit `.env`.

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

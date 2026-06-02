# GoodEnoughLLMs

GoodEnoughLLMs is both an Agent Skill and a small Python CLI for ranking Artificial Analysis model data by value score.

It prints the top 5 cheapest models that still clear the selected effort threshold for both:

- Agentic Track
- Coding Track

The score used for each track is divided by `price_1m_blended_3_to_1` to compute a value score.

## Agent Skill

The skill lives in `.agents/skills/goodenoughllms/` and can be invoked by compatible clients with:

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

The skill delegates to the canonical Python implementation, so skill usage and direct CLI usage stay in sync.

## Direct CLI

You can also run the script directly:

```bash
python3 aa_top5.py
python3 aa_top5.py --effort high
python3 aa_top5.py --effort xhigh --provider OpenAI
python3 aa_top5.py --provider Anthropic
python3 aa_top5.py --help
```

Supported flags:

- `--effort low|medium|high|xhigh` selects the minimum threshold as a percentage of the best available score for each track.
- `--provider <name>` filters models by `model_creator.name` using a case-insensitive substring match.
- `--help` shows usage, examples, and the AA_KEY lookup order.

No third-party Python packages are required.

Default effort is `medium`.

## Effort thresholds

| Effort | Minimum score threshold |
| ------ | ----------------------- |
| low | 70% of the best available score |
| medium | 80% of the best available score |
| high | 90% of the best available score |
| xhigh | 99% of the best available score |

## API key

The tool reads `AA_KEY` in this order:

1. Process environment
2. Global user config file at `$XDG_CONFIG_HOME/goodenoughllms/.env`
3. If `XDG_CONFIG_HOME` is unset, `~/.config/goodenoughllms/.env`

Example line in the global config file:

```text
AA_KEY=your_api_key_here
```

No repo-local `.env` file is required. Do not commit API keys to the repository.

If the key is missing, the tool prints a short onboarding message and exits without making an API call.

## Notes

- The Agentic Track uses the Artificial Analysis Intelligence Index.
- The Coding Track uses the Artificial Analysis Coding Index.
- If a provider filter removes all models, the tool exits with a clear error.
- The output ends with the Artificial Analysis credit line.

## Data source

Data provided by Artificial Analysis - https://artificialanalysis.ai/

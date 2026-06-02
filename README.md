# GoodEnoughLLMs

GoodEnoughLLMs is an Agent Skill for ranking Artificial Analysis model data by value score.

Use it by invoking the skill in a compatible client:

```text
/goodenoughllms
```

`SKILL.md` in the repository root is the authoritative usage guide.

GoodEnoughLLMs looks for `AA_KEY` in this order:

1. Process environment
2. Skill-local `.env` in the repository root, next to `SKILL.md`

The repository includes `.env.example`:

```text
AA_KEY=your_artificial_analysis_api_key_here
```

Copy it to `.env`, replace the placeholder with your real Artificial Analysis API key, and do not commit `.env`.

Internally, the skill uses the existing Python implementation in `aa_top5.py`. For local debugging only, run:

```bash
python3 scripts/goodenoughllms.py --help
```

Key facts:

- Agentic Track uses the Artificial Analysis Intelligence Index.
- Coding Track uses the Artificial Analysis Coding Index.
- Effort levels: `low`, `medium`, `high`, `xhigh`.
- Optional provider filter matches `model_creator.name` case-insensitively.
- Output ends with the Artificial Analysis credit line.

Data provided by Artificial Analysis - https://artificialanalysis.ai/

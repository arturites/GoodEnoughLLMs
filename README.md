# GoodEnoughLLMs

GoodEnoughLLMs is an Agent Skill for ranking Artificial Analysis model data by value score.
The `quality` parameter sets the minimum acceptable model quality relative to the best available Intelligence Index or Coding Index in a track. It does not describe reasoning budget or thinking time.

Use it by invoking the skill in a compatible client:

```text
/goodenoughllms
/goodenoughllms --quality good
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

Internally, the skill uses the existing Python implementation in `scripts/aa_top5.py`. For local debugging only, run:

```bash
python3 scripts/aa_top5.py --help
python3 scripts/aa_top5.py --quality good
```

Key facts:

- Agentic Track uses the Artificial Analysis Intelligence Index.
- Coding Track uses the Artificial Analysis Coding Index.
- Quality levels: `basic`, `good`, `high`, `max`.
- Optional provider filter matches `model_creator.name` case-insensitively.
- Output ends with the Artificial Analysis credit line.

Quality levels:

- `basic`: 60% of the best available model in the track. Good for simple tasks, everyday questions, very cheap models, and maximum cost savings.
- `good`: 80% of the best available model in the track. The Pareto sweet spot and the default. "80% of the performance for a fraction of the cost." Good for most users and daily work.
- `high`: 90% of the best available model in the track. Good for demanding tasks, architecture decisions, complex analysis, difficult coding, and higher-requirement agents.
- `max`: 99% of the best available model in the track. Good for critical tasks, difficult agents, and maximum quality. "If only the best models are acceptable."

Data provided by Artificial Analysis - https://artificialanalysis.ai/

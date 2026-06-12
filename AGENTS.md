# AGENTS.md

- This repo is a single Python skill. `SKILL.md` is the behavior spec; `README.md` is the overview; `scripts/aa_top5.py` is the only runnable entrypoint.
- No build, test, lint, typecheck, or CI manifests exist in the current tree. Do not invent package-manager or test-runner commands.
- Runtime assumptions: Python 3.11+ and network access to Artificial Analysis.
- `AA_KEY` is read from the process environment first, then from `.env` in the repo root next to `SKILL.md`. Copy `.env.example` to `.env`; keep `.env` uncommitted.
- Zero-key smoke test: `python3 scripts/aa_top5.py --help`.
- Live check: `python3 scripts/aa_top5.py --quality good` requires `AA_KEY`.
- Missing `AA_KEY` should print onboarding to stderr and exit non-zero without calling the API.
- `--provider` is a case-insensitive substring filter on `model_creator.name`, not an exact match.
- `quality` is a threshold (`basic|good|high|max`) relative to the best model in each track, not a reasoning-budget knob.
- The script discovers the repo root by walking upward from `scripts/aa_top5.py` until it finds `SKILL.md`; keep that layout unless you update the lookup.
- The output has separate Agentic and Coding tracks and should keep the final Artificial Analysis credit line intact.

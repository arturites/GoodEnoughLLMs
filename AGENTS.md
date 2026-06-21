# AGENTS.md

- This repo is a single Python CLI tool. `goodenoughllms.py` is the only runnable entrypoint; `README.md` is the user-facing guide.
- No build, test, lint, typecheck, or CI manifests exist in the current tree. Do not invent package-manager or test-runner commands.
- Runtime assumptions: Python 3.11+ and network access to Artificial Analysis.
- `AA_KEY` is read from the process environment first, then from `.env` in the repo root next to `goodenoughllms.py`. Copy `.env.example` to `.env`; keep `.env` uncommitted.
- Zero-key smoke tests: `python3 goodenoughllms.py --help` and `python3 goodenoughllms.py --version`.
- Live check: `python3 goodenoughllms.py --quality good` requires `AA_KEY`.
- Missing `AA_KEY` should print onboarding to stderr and exit with code `3` without calling the API.
- `--provider` is a case-insensitive substring filter on `model_creator.name`, not an exact match.
- `quality` is a threshold (`basic|good|high|max`) relative to the best model in each track, not a reasoning-budget knob.
- Default output is human-readable ASCII tables; `--json` is machine-readable and should emit valid JSON on stdout on success.
- The output has separate Agentic and Coding tracks and should keep the final Artificial Analysis credit line intact for human output, or expose it as a JSON field for `--json`.

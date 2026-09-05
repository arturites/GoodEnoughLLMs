# AGENTS.md

- This repo is a single Python CLI tool. `goodenoughllms.py` is the implementation entrypoint, `gelm` is the installed console command, and `README.md` is the user-facing guide.
- `pyproject.toml` is the packaging manifest. No test, lint, typecheck, or CI manifests exist; do not invent package-manager or test-runner commands.
- Runtime assumptions: Python 3.11+ and network access to Artificial Analysis.
- `AA_KEY` is read from the process environment first, then from `~/.goodenoughllms/.env`. Direct source-tree execution keeps the repository `.env` as a legacy fallback. The installed CLI creates the profile file and securely prompts for a missing key in an interactive terminal.
- Zero-key smoke tests: `python3 goodenoughllms.py --help` and `python3 goodenoughllms.py --version`.
- Live check: `python3 goodenoughllms.py --quality good` requires `AA_KEY`.
- Missing `AA_KEY` should prompt only for an interactive human invocation; otherwise it should print onboarding to stderr and exit with code `3` without calling the API.
- `--provider` is a case-insensitive substring filter on `model_creator.name`, not an exact match.
- `quality` is a threshold (`basic|good|high|max`) relative to the best model in each track, not a reasoning-budget knob.
- Default output is human-readable ASCII tables; `--json` is machine-readable and should emit valid JSON on stdout on success.
- The output has separate Agentic and Coding tracks and should keep the final Artificial Analysis credit line intact for human output, or expose it as a JSON field for `--json`.

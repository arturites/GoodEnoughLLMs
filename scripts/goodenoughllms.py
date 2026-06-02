#!/usr/bin/env python3
"""Thin skill wrapper that delegates to the canonical implementation in aa_top5.py."""

from __future__ import annotations

import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "aa_top5.py").is_file():
            return candidate
    raise RuntimeError("Could not locate aa_top5.py from the skill wrapper.")


def main(argv: list[str] | None = None) -> int:
    try:
        repo_root = find_repo_root(Path(__file__).resolve())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    from aa_top5 import main as aa_main

    return aa_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

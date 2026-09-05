# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-09-05

### Added

- Install the CLI with pipx and run it with the `gelm` command.
- Create `~/.goodenoughllms/.env` automatically on the first normal invocation.
- Ask interactively for a missing Artificial Analysis API key and store it securely.

### Changed

- Use the per-user configuration file as the primary API-key location.
- Keep direct source-tree execution available through `python3 goodenoughllms.py`.

[unreleased]: https://github.com/arturites/GoodEnoughLLMs/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/arturites/GoodEnoughLLMs/compare/v2.0.0...v2.1.0

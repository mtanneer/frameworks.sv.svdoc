# Contributing

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
git config core.hooksPath scripts/hooks  # runs `ruff format` on commit
```

## Workflow

- All changes go through a feature branch + PR into `main` — `main` is
  protected (no direct pushes, no force-push).
- Before opening a PR: `ruff check .` and `python -m pytest` (or `make
  check`) must pass.
- If your change adds/removes/renames a public CLI flag, command, IR field,
  or public function/class, update `README.md` and `docs/` in the same PR.
- Keep PRs scoped to one change; update `CHANGELOG.md` under `[Unreleased]`
  for anything user-facing.

## Reporting bugs / proposing features

Open a GitHub issue. Include the `.sv` snippet that reproduces the problem
where relevant — this project is parser-heavy, and most bugs so far have
been found by throwing real RTL at it.

## License

By contributing, you agree your contributions are licensed under the MIT
License (see `LICENSE`).

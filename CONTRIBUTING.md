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

## Stability and deprecation

What is public (CLI flags, documented Python API, IR fields) is defined in
`docs/stability.rst`. From 1.0 it follows semver:

- Removing or renaming public surface needs a deprecation first: keep the old
  name working for at least one minor release, emit a `DeprecationWarning`
  (Python API) or a stderr warning (CLI flag), and note it under
  `### Deprecated` in `CHANGELOG.md`. Removal happens in the next major.
- IR changes in 1.x are additive only (new fields with defaults).
- Generated-output markup is not covered; refine it freely, but note visible
  changes in the changelog.

## Reporting bugs / proposing features

Open a GitHub issue. Include the `.sv` snippet that reproduces the problem
where relevant — this project is parser-heavy, and most bugs so far have
been found by throwing real RTL at it.

## License

By contributing, you agree your contributions are licensed under the MIT
License (see `LICENSE`).

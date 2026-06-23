# Agent Notes — NVIDIA Skills Directory

## Project type
Documentation/generator repo. The only source of truth for skill data is `nvidia_skills_catalog.json`; `DIRECTORY.md`, `nvidia_skills_catalog.md`, and `nvidia_skills_summary.md` are generated or derived artifacts.

## Key files
- `nvidia_skills_catalog.json` — source-of-truth extract from `NVIDIA/skills@366564ddf68ad55b3c12a2faee3d2fd3d3de3b36`. Do not hand-edit.
- `scripts/extract_catalog.py` — extracts the latest skill catalog from the upstream `NVIDIA/skills` repo.
- `scripts/update_pin.py` — updates the pinned commit hash and total count constants after extraction.
- `scripts/generate_directory.py` — regenerates `DIRECTORY.md` from the JSON catalog.
- `tests/test_directory.py` — acceptance tests for `DIRECTORY.md` structure and completeness.
- `DIRECTORY.md` — generated canonical catalog (this repo's `readme` in `pyproject.toml`).
- `.github/workflows/sync-upstream.yml` — weekly GitHub Actions workflow that extracts the latest catalog, updates pins, regenerates `DIRECTORY.md`, and opens a PR when upstream changes.

## Commands
```bash
# Extract catalog from upstream
uv run scripts/extract_catalog.py

# Update pinned constants after extraction
uv run scripts/update_pin.py <commit> <total>

# Regenerate the directory
uv run scripts/generate_directory.py

# Run tests
uv run pytest tests/test_directory.py -v

# Quality gates (must all pass before pushing)
uv run ruff check scripts tests
uv run ruff format --check scripts tests
uv run basedpyright
```

## Tooling quirks
- `uv` is required. The generator script uses PEP 723 inline metadata, so `uv run scripts/generate_directory.py` works without a manual venv.
- `basedpyright` only includes `scripts` and `tests`; generated markdown files are not type-checked.
- `pytest` `pythonpath = ["."]` lets tests import `scripts.generate_directory`. Do not move `scripts/` without updating `pyproject.toml`.
- `ruff` `src = ["scripts", "tests"]`; treat both as first-class source.

## Editing rules
- Never edit `DIRECTORY.md` by hand. Change `scripts/generate_directory.py` and rerun.
- The pinned commit hash `366564ddf68ad55b3c12a2faee3d2fd3d3de3b36` is hardcoded in both the generator and tests. If you update the catalog source, update both.
- The catalog JSON is an external snapshot. Refresh it locally by running the extraction logic, updating the pinned constants, and regenerating the directory:
  ```bash
  uv run scripts/extract_catalog.py
  uv run scripts/update_pin.py "$(jq -r .commit nvidia_skills_catalog.json)" "$(jq -r .total nvidia_skills_catalog.json)"
  uv run scripts/generate_directory.py
  ```
  A weekly GitHub Actions workflow (`.github/workflows/sync-upstream.yml`) performs the same steps and opens a PR when upstream changes.

## MCP servers
This repo catalogs NVIDIA skills, not MCP servers. Both the upstream `NVIDIA/skills` repo and this workspace contain zero MCP server implementations.

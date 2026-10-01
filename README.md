# cfb-modeling

Cutoff-aware college football forecasting built on CollegeFootballData (CFBD). It produces immutable CFBD ingestion, strict temporal snapshots, coherent joint final-score distributions, deterministic picks, and forward evaluation.

**Status:** this is scaffolding and contract tests only. No model has been fitted and no forecasting performance has been demonstrated. See [PROGRESS.md](PROGRESS.md).

## Specification

The working specification is [docs/blueprint/](docs/blueprint/README.md) (v1.0, 2026-10-01). Any departure from it is logged with its statistical justification in [docs/deviations.md](docs/deviations.md). The working copies of `config/config.json` and `src/cfb/db/schema.sql` are byte-checked against the blueprint by `tests/contracts/test_spec_sync.py`.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). Run every command from the repo root: `uv run` finds the project, and its `cfb` command, from the current directory. From elsewhere, use `uv run --project D:\cfb-modeling cfb ...`.

1. Install the dependencies:

   ```powershell
   cd D:\cfb-modeling
   uv sync --extra dev
   ```

2. Set your CFBD key. The key is never written to config, logs, or the ledger.

   ```powershell
   [Environment]::SetEnvironmentVariable("CFBD_API_KEY", "<your key>", "User")   # persistent
   # or a git-ignored .env at the repo root:  CFBD_API_KEY=<your key>
   ```

3. Check the setup and run the tests:

   ```powershell
   uv run cfb doctor
   uv run pytest
   ```

Without a key, everything except live ingestion still runs. Tests marked `live` are skipped.

## Real vs synthetic data

- Requests to CFBD are recorded with `provider = 'CFBD'`.
- Fabricated fixtures in `tests/fixtures/synthetic/` use `provider = 'SYNTHETIC'`.
- Synthetic data exercises contracts and parameter recovery only. No performance claim is ever made from it.

## Layout

```text
config/          working config (proposed defaults, not tuned)
docs/blueprint/  specification (read-only reference)
src/cfb/         ingestion, canonical, snapshots, state, features, models,
                 stacking, decisions, evaluation, views, operations, db
tests/           contracts, temporal, transitions, numerical, replay
data/ artifacts/ local only, git-ignored
experiments/     registered protocols and evaluation results
```

## License

MIT, Caleb Vinson 2026.

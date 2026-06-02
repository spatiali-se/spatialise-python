# Prod v2 smoke test (manual operator script)

`smoke_v2.py` empirically confirms that a **fresh PyPI install** of
`spatialise==0.3.0` drives a v2-routed batch end-to-end against **prod**
(SPA-1799). It is a one-shot operator script — **never run by CI**.

## Safety

- Not a pytest test and not collected by CI (`testpaths = ["tests"]`).
- **Refuses to run under CI** (`$CI` set) and **refuses without prod config**
  (`SPATIALISE_PROD_BASE_URL` + `SPATIALISE_API_KEY`). A bare invocation does
  no network I/O and exits non-zero.

## How an operator runs it

```sh
# 1. Clean venv with ONLY the published artifact (not an editable checkout)
python -m venv /tmp/smoke && . /tmp/smoke/bin/activate
pip install "spatialise==0.3.0"

# 2. Provide prod config (see "Open / ask-first items")
export SPATIALISE_PROD_BASE_URL="…"   # TODO: prod v2 base URL
export SPATIALISE_API_KEY="…"         # TODO: prod API key

# 3. Run
python scripts/smoke/smoke_v2.py
```

It creates a canary batch, polls `retrieve_status` printing per-job patch-batch
progress (`completed_patch_batches`/`total_patch_batches`, added in SPA-1797),
waits for a terminal status, then reports teardown.

## Open / ask-first items (must be resolved before a real run)

- **Prod v2 base URL** and **API key** — not hardcoded; supplied via env.
- **Canary payload** — `_build_canary_jobs()` currently raises `NotImplementedError`.
  Confirm a no-op / no-billable-inference payload shape with the backend, or pair
  it with a teardown that guarantees no orphaned/costly prod job.
- **Gating** — only meaningful after `0.3.0` is published (SPA-1798) **and** Cloud
  Tasks Q1 routes to the v2 flow (SPA-1665). Until then, a failure is not a client bug.

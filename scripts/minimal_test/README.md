# Minimal v2 end-to-end test (manual operator script)

`minimal_test_v2.py` is the minimal "does a v2 batch round-trip at all?" check: it
confirms that a **fresh PyPI install** of `spatialise==0.3.0` drives a v2-routed
batch end-to-end against a **live v2 host** (SPA-1799). It is a one-shot operator
script — **never run by CI**.

Point it at the v2 host with whatever key you've been given — a **dev key against
the dev/v2 host** is the expected first run (per the launch roadmap); the same
script works against prod once that's the target.

This is the minimal liveness test, **not** the full suite. The fuller test matrix —
multiple concurrent batches, varying polygon sizes, prediction/area-consumption
consistency vs prior v2 manual runs, and rejection/edge cases — is tracked separately.

## Safety

- Not a pytest test and not collected by CI (`testpaths = ["tests"]`).
- **Refuses to run under CI** (`$CI` set) and **refuses without config**
  (`SPATIALISE_BASE_URL` + `SPATIALISE_API_KEY`). A bare invocation does no
  network I/O and exits non-zero.

## How an operator runs it

```sh
# 1. Clean venv with ONLY the published artifact (not an editable checkout)
python -m venv /tmp/mintest && . /tmp/mintest/bin/activate
pip install "spatialise==0.3.0"

# 2. Provide the target config (see "Open / ask-first items")
export SPATIALISE_BASE_URL="…"   # TODO: v2 base URL (dev or prod v2 host)
export SPATIALISE_API_KEY="…"    # TODO: API key for that host

# 3. Run
python scripts/minimal_test/minimal_test_v2.py
```

It creates a canary batch, polls `retrieve_status` printing per-job patch-batch
progress (`completed_patch_batches`/`total_patch_batches`, added in SPA-1797),
waits for a terminal status, then reports teardown.

## Open / ask-first items (must be resolved before a real run)

- **v2 base URL** and **API key** — not hardcoded; supplied via env (dev key first).
- **Canary payload** — `_build_canary_jobs()` currently raises `NotImplementedError`.
  Confirm a no-op / no-billable-inference payload shape with the backend, or pair
  it with a teardown that guarantees no orphaned/costly job.
- **Gating** — only meaningful after `0.3.0` is published (SPA-1798) **and** the v2
  host is live: the dispatcher has `V2_DISPATCH_HOST` (+ `EE_GET_DATA_QUEUE_NAME`)
  set and `soilpredict-v2.api` resolves to the LB. Until then, a failure is not a
  client bug.

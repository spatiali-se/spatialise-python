#!/usr/bin/env python3
"""One-shot operator smoke test: a fresh PyPI install of ``spatialise==0.3.0``
driving a v2-routed batch end-to-end against PROD.

This is a MANUAL operator script (SPA-1799). It is intentionally NOT a pytest
test and is never collected by CI (``testpaths = ["tests"]`` in pyproject.toml).
It refuses to run unless explicit prod env vars are set, and hard-refuses under
CI, so it can never fire ``batch.create`` against prod by accident.

Intended flow (performed by a human operator, not in this repo's automation):

  1. Create a clean virtualenv and install the published artifact ONLY:
         python -m venv /tmp/smoke && . /tmp/smoke/bin/activate
         pip install "spatialise==0.3.0"          # real PyPI, NOT an editable checkout
  2. Export the prod config (see "Required environment" below).
  3. python scripts/smoke/smoke_v2.py
     -> client.batch.create(<canary>) against the prod v2 base URL
     -> poll retrieve_status(batch_id), printing patch-batch progress each poll
        (job.completed_patch_batches / job.total_patch_batches, added in SPA-1797)
     -> on terminal status, tear the batch down so no prod job is orphaned.

Required environment (the "ask first" items from the ticket — fill in before running):
  SPATIALISE_PROD_BASE_URL   prod v2 base URL                          # TODO: confirm
  SPATIALISE_API_KEY         prod API key / bearer token               # TODO: provide

Gating: this smoke test is only meaningful once 0.3.0 is published (SPA-1798) AND
Cloud Tasks Q1 routes to the v2 flow (SPA-1665). Do not treat a failure as a client
bug until both are in place.
"""

from __future__ import annotations

import os
import sys
import time

# Polling knobs (operator's call — tune as needed).
POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
TERMINAL_STATUSES = {"completed", "failed", "partially_failed"}

# Env var names for prod config.
ENV_BASE_URL = "SPATIALISE_PROD_BASE_URL"
ENV_API_KEY = "SPATIALISE_API_KEY"


def _refuse(message: str) -> "NoReturn":  # type: ignore[name-defined]  # noqa: F821
    """Print why we're refusing and exit non-zero WITHOUT doing any network I/O."""
    print(f"smoke_v2: refusing to run — {message}", file=sys.stderr)
    raise SystemExit(2)


def _build_canary_jobs() -> list:
    """The canary payload for batch.create.

    TODO (ask-first): confirm a no-op / no-billable-inference canary shape with the
    backend before running against prod. A job is ``{"polygon": {...}, "year": int}``
    (see spatialise.types.batch_create_params). The placeholder below is a tiny
    polygon and MUST be replaced with an agreed canary that incurs no real inference
    cost, or paired with the teardown step so no billable prod job lingers.
    """
    raise NotImplementedError(
        "Canary payload not yet defined — confirm a no-op/no-cost shape (SPA-1799 ask-first)."
    )


def main() -> None:
    # Guard 1: never run from CI.
    if os.environ.get("CI"):
        _refuse("running under CI ($CI is set); this script must never hit prod from CI.")

    # Guard 2: require explicit prod config — no defaults, no hardcoded prod URL/secret.
    base_url = os.environ.get(ENV_BASE_URL)
    api_key = os.environ.get(ENV_API_KEY)
    if not base_url or not api_key:
        _refuse(
            f"missing prod config. Set {ENV_BASE_URL} and {ENV_API_KEY} "
            "to the prod v2 base URL and API key before running."
        )

    # Import only after the guards pass, so a bare invocation does nothing.
    from spatialise import SpatialiseSoilPrediction

    client = SpatialiseSoilPrediction(api_key=api_key, base_url=base_url)

    print(f"smoke_v2: creating canary batch against {base_url}")
    created = client.batch.create(jobs=_build_canary_jobs())
    batch_id = created.batch_id
    if not batch_id:
        print("smoke_v2: FAIL — batch.create returned an empty batch id", file=sys.stderr)
        raise SystemExit(1)
    print(f"smoke_v2: batch_id={batch_id}")

    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    final_status = None
    try:
        while True:
            status = client.batch.retrieve_status(batch_id)
            # Per-job patch-batch progress (SPA-1797) — visible while the job runs.
            for job in status.jobs:
                if job.total_patch_batches:
                    done = job.completed_patch_batches or 0
                    print(f"  job {job.job_id}: {done}/{job.total_patch_batches} patch-batches "
                          f"({job.status})")
            print(f"smoke_v2: batch status={status.status} "
                  f"({status.completed_jobs}/{status.total_jobs} jobs done)")

            if status.status in TERMINAL_STATUSES:
                final_status = status.status
                break
            if time.monotonic() > deadline:
                print(f"smoke_v2: TIMEOUT after {POLL_TIMEOUT_SECONDS}s "
                      f"(last status={status.status})", file=sys.stderr)
                raise SystemExit(1)
            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        # Teardown: never leave an orphaned prod job. There is no cancel endpoint in
        # the 0.3.0 contract, so the canary MUST be a documented no-op/no-cost payload
        # (see _build_canary_jobs TODO). Surface what was left behind for the operator.
        print(f"smoke_v2: teardown — batch {batch_id} reached {final_status!r}. "
              "Ensure the canary payload incurs no billable inference / leaves no orphan.")

    print(f"smoke_v2: DONE — terminal status {final_status!r}")


if __name__ == "__main__":
    main()

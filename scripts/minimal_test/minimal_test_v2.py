#!/usr/bin/env python3
"""Minimal end-to-end test: a fresh PyPI install of ``spatialise==0.3.0`` driving
a v2-routed batch end-to-end against a live v2 host.

This is a MANUAL operator script (SPA-1799) — the minimal "does a v2 batch
round-trip at all?" liveness check, run by a human after the v2 host is live. It
is intentionally NOT a pytest test and is never collected by CI
(``testpaths = ["tests"]`` in pyproject.toml). It refuses to run unless an
explicit base URL + API key are set, and hard-refuses under CI, so it can never
fire ``batch.create`` by accident.

Point it at the v2 host with whatever key you've been given — a dev key against
the dev/v2 host is the expected first run (see the launch roadmap); the same
script works against prod once that's the target. It does NOT replace the fuller
test matrix (concurrency, polygon sizes, prediction/area-consumption consistency,
rejection edge cases) — that is tracked separately.

Intended flow (performed by a human operator, not in this repo's automation):

  1. Create a clean virtualenv and install the published artifact ONLY:
         python -m venv /tmp/mintest && . /tmp/mintest/bin/activate
         pip install "spatialise==0.3.0"          # real PyPI, NOT an editable checkout
  2. Export the target config (see "Required environment" below).
  3. python scripts/minimal_test/minimal_test_v2.py
     -> client.batch.create(<canary>) against the v2 base URL
     -> poll retrieve_status(batch_id); for each job, retrieve_job_status(...)
        to print patch-batch progress (completed_patch_batches /
        total_patch_batches, added in SPA-1797)
     -> on terminal status, tear the batch down so no job is orphaned.

Required environment (the "ask first" items from the ticket — fill in before running):
  SPATIALISE_BASE_URL   v2 base URL (dev or prod v2 host)               # TODO: confirm
  SPATIALISE_API_KEY    API key / bearer token for that host            # TODO: provide

Gating: this test is only meaningful once 0.3.0 is published (SPA-1798) AND the v2
host is live — i.e. the dispatcher has ``V2_DISPATCH_HOST`` (+ ``EE_GET_DATA_QUEUE_NAME``)
set and the ``soilpredict-v2.api`` DNS record resolves to the LB. Do not treat a
failure as a client bug until both are in place.
"""

from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spatialise.types.batch_create_params import Job

# Polling knobs (operator's call — tune as needed).
POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
TERMINAL_STATUSES = {"completed", "failed", "partially_failed"}

# Env var names for the target config (dev or prod v2 host).
ENV_BASE_URL = "SPATIALISE_BASE_URL"
ENV_API_KEY = "SPATIALISE_API_KEY"


def _refuse(message: str) -> "NoReturn":  # type: ignore[name-defined]  # noqa: F821
    """Print why we're refusing and exit non-zero WITHOUT doing any network I/O."""
    print(f"minimal_test_v2: refusing to run — {message}", file=sys.stderr)
    raise SystemExit(2)


def _build_canary_jobs() -> "list[Job]":
    """The canary payload for batch.create.

    TODO (ask-first): confirm a no-op / no-billable-inference canary shape with the
    backend before running. A job is ``{"polygon": {...}, "year": int}`` (see
    spatialise.types.batch_create_params). The placeholder below is a tiny polygon
    and MUST be replaced with an agreed canary that incurs no real inference cost,
    or paired with the teardown step so no billable job lingers.
    """
    raise NotImplementedError("Canary payload not yet defined — confirm a no-op/no-cost shape (SPA-1799 ask-first).")


def main() -> None:
    # Guard 1: never run from CI.
    if os.environ.get("CI"):
        _refuse("running under CI ($CI is set); this script must never hit a live host from CI.")

    # Guard 2: require explicit config — no defaults, no hardcoded URL/secret.
    base_url = os.environ.get(ENV_BASE_URL)
    api_key = os.environ.get(ENV_API_KEY)
    if not base_url or not api_key:
        _refuse(
            f"missing config. Set {ENV_BASE_URL} and {ENV_API_KEY} "
            "to the v2 base URL and API key before running."
        )

    # Import only after the guards pass, so a bare invocation does nothing.
    from spatialise import SpatialiseSoilPrediction

    client = SpatialiseSoilPrediction(api_key=api_key, base_url=base_url)

    print(f"minimal_test_v2: creating canary batch against {base_url}")
    created = client.batch.create(jobs=_build_canary_jobs())
    batch_id = created.batch_id
    if not batch_id:
        print("minimal_test_v2: FAIL — batch.create returned an empty batch id", file=sys.stderr)
        raise SystemExit(1)
    print(f"minimal_test_v2: batch_id={batch_id}")

    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    final_status = None
    try:
        while True:
            status = client.batch.retrieve_status(batch_id)
            # Per-job patch-batch progress (SPA-1797): the counts live on the
            # job-detail endpoint, not on the batch-status Job, so fetch them per job.
            for job in status.jobs:
                detail = client.batch.retrieve_job_status(job.job_id, batch_id=batch_id)
                if detail.total_patch_batches:
                    done = detail.completed_patch_batches or 0
                    print(
                        f"  job {job.job_id}: {done}/{detail.total_patch_batches} "
                        f"patch-batches ({job.status})"
                    )
            print(
                f"minimal_test_v2: batch status={status.status} "
                f"({status.completed_jobs}/{status.total_jobs} jobs done)"
            )

            if status.status in TERMINAL_STATUSES:
                final_status = status.status
                break
            if time.monotonic() > deadline:
                print(
                    f"minimal_test_v2: TIMEOUT after {POLL_TIMEOUT_SECONDS}s (last status={status.status})",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        # Teardown: never leave an orphaned job. There is no cancel endpoint in the
        # 0.3.0 contract, so the canary MUST be a documented no-op/no-cost payload
        # (see _build_canary_jobs TODO). Surface what was left behind for the operator.
        print(
            f"minimal_test_v2: teardown — batch {batch_id} reached {final_status!r}. "
            "Ensure the canary payload incurs no billable inference / leaves no orphan."
        )

    print(f"minimal_test_v2: DONE — terminal status {final_status!r}")


if __name__ == "__main__":
    main()

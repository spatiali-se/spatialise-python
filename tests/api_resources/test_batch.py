# This file is part of the spatialise SDK and is maintained by hand.

from __future__ import annotations

import os
from typing import Any, cast
from datetime import datetime, timezone

import pytest

from spatialise import SpatialiseSoilPrediction, AsyncSpatialiseSoilPrediction
from tests.utils import assert_matches_type
from spatialise.types import (
    BatchCreateResponse,
    PatchBatchStatusInfo,
    JobDetailStatusResponse,
    BatchRetrieveStatusResponse,
)
from spatialise._models import construct_type

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestBatch:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    def test_method_create(self, client: SpatialiseSoilPrediction) -> None:
        batch = client.batch.create(
            jobs=[
                {
                    "polygon": {"coordinates": [[[0]]]},
                    "year": 2018,
                }
            ],
        )
        assert_matches_type(BatchCreateResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    def test_method_create_with_all_params(self, client: SpatialiseSoilPrediction) -> None:
        batch = client.batch.create(
            jobs=[
                {
                    "polygon": {
                        "coordinates": [[[0]]],
                        "type": "Polygon",
                    },
                    "year": 2018,
                }
            ],
            metadata={"foo": "bar"},
            webhook_url="webhook_url",
            webhook_secret="Webhook-Secret",
        )
        assert_matches_type(BatchCreateResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    def test_raw_response_create(self, client: SpatialiseSoilPrediction) -> None:
        response = client.batch.with_raw_response.create(
            jobs=[
                {
                    "polygon": {"coordinates": [[[0]]]},
                    "year": 2018,
                }
            ],
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        batch = response.parse()
        assert_matches_type(BatchCreateResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    def test_streaming_response_create(self, client: SpatialiseSoilPrediction) -> None:
        with client.batch.with_streaming_response.create(
            jobs=[
                {
                    "polygon": {"coordinates": [[[0]]]},
                    "year": 2018,
                }
            ],
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            batch = response.parse()
            assert_matches_type(BatchCreateResponse, batch, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_method_retrieve_status(self, client: SpatialiseSoilPrediction) -> None:
        batch = client.batch.retrieve_status(
            batch_id="batch_id",
        )
        assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_method_retrieve_status_with_all_params(self, client: SpatialiseSoilPrediction) -> None:
        batch = client.batch.retrieve_status(
            batch_id="batch_id",
            cursor="cursor",
            limit=0,
        )
        assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_raw_response_retrieve_status(self, client: SpatialiseSoilPrediction) -> None:
        response = client.batch.with_raw_response.retrieve_status(
            batch_id="batch_id",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        batch = response.parse()
        assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_streaming_response_retrieve_status(self, client: SpatialiseSoilPrediction) -> None:
        with client.batch.with_streaming_response.retrieve_status(
            batch_id="batch_id",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            batch = response.parse()
            assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_path_params_retrieve_status(self, client: SpatialiseSoilPrediction) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `batch_id` but received ''"):
            client.batch.with_raw_response.retrieve_status(
                batch_id="",
            )

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_method_retrieve_job_status(self, client: SpatialiseSoilPrediction) -> None:
        batch = client.batch.retrieve_job_status(
            job_id="job_id",
            batch_id="batch_id",
        )
        assert_matches_type(JobDetailStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_method_retrieve_job_status_with_all_params(self, client: SpatialiseSoilPrediction) -> None:
        batch = client.batch.retrieve_job_status(
            job_id="job_id",
            batch_id="batch_id",
            cursor="cursor",
            limit=0,
        )
        assert_matches_type(JobDetailStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_path_params_retrieve_job_status(self, client: SpatialiseSoilPrediction) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `batch_id` but received ''"):
            client.batch.with_raw_response.retrieve_job_status(
                job_id="job_id",
                batch_id="",
            )

        with pytest.raises(ValueError, match=r"Expected a non-empty value for `job_id` but received ''"):
            client.batch.with_raw_response.retrieve_job_status(
                job_id="",
                batch_id="batch_id",
            )

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_method_retrieve_patch_batch_status(self, client: SpatialiseSoilPrediction) -> None:
        batch = client.batch.retrieve_patch_batch_status(
            patch_batch_idx=0,
            batch_id="batch_id",
            job_id="job_id",
        )
        assert_matches_type(PatchBatchStatusInfo, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    def test_path_params_retrieve_patch_batch_status(self, client: SpatialiseSoilPrediction) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `batch_id` but received ''"):
            client.batch.with_raw_response.retrieve_patch_batch_status(
                patch_batch_idx=0,
                batch_id="",
                job_id="job_id",
            )

        with pytest.raises(ValueError, match=r"Expected a non-empty value for `job_id` but received ''"):
            client.batch.with_raw_response.retrieve_patch_batch_status(
                patch_batch_idx=0,
                batch_id="batch_id",
                job_id="",
            )


class TestAsyncBatch:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    async def test_method_create(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        batch = await async_client.batch.create(
            jobs=[
                {
                    "polygon": {"coordinates": [[[0]]]},
                    "year": 2018,
                }
            ],
        )
        assert_matches_type(BatchCreateResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    async def test_method_create_with_all_params(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        batch = await async_client.batch.create(
            jobs=[
                {
                    "polygon": {
                        "coordinates": [[[0]]],
                        "type": "Polygon",
                    },
                    "year": 2018,
                }
            ],
            metadata={"foo": "bar"},
            webhook_url="webhook_url",
            webhook_secret="Webhook-Secret",
        )
        assert_matches_type(BatchCreateResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    async def test_raw_response_create(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        response = await async_client.batch.with_raw_response.create(
            jobs=[
                {
                    "polygon": {"coordinates": [[[0]]]},
                    "year": 2018,
                }
            ],
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        batch = await response.parse()
        assert_matches_type(BatchCreateResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism doesn't support callbacks yet")
    @parametrize
    async def test_streaming_response_create(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        async with async_client.batch.with_streaming_response.create(
            jobs=[
                {
                    "polygon": {"coordinates": [[[0]]]},
                    "year": 2018,
                }
            ],
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            batch = await response.parse()
            assert_matches_type(BatchCreateResponse, batch, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_method_retrieve_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        batch = await async_client.batch.retrieve_status(
            batch_id="batch_id",
        )
        assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_method_retrieve_status_with_all_params(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        batch = await async_client.batch.retrieve_status(
            batch_id="batch_id",
            cursor="cursor",
            limit=0,
        )
        assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_raw_response_retrieve_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        response = await async_client.batch.with_raw_response.retrieve_status(
            batch_id="batch_id",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        batch = await response.parse()
        assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_streaming_response_retrieve_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        async with async_client.batch.with_streaming_response.retrieve_status(
            batch_id="batch_id",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            batch = await response.parse()
            assert_matches_type(BatchRetrieveStatusResponse, batch, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_path_params_retrieve_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `batch_id` but received ''"):
            await async_client.batch.with_raw_response.retrieve_status(
                batch_id="",
            )

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_method_retrieve_job_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        batch = await async_client.batch.retrieve_job_status(
            job_id="job_id",
            batch_id="batch_id",
        )
        assert_matches_type(JobDetailStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_method_retrieve_job_status_with_all_params(
        self, async_client: AsyncSpatialiseSoilPrediction
    ) -> None:
        batch = await async_client.batch.retrieve_job_status(
            job_id="job_id",
            batch_id="batch_id",
            cursor="cursor",
            limit=0,
        )
        assert_matches_type(JobDetailStatusResponse, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_path_params_retrieve_job_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `batch_id` but received ''"):
            await async_client.batch.with_raw_response.retrieve_job_status(
                job_id="job_id",
                batch_id="",
            )

        with pytest.raises(ValueError, match=r"Expected a non-empty value for `job_id` but received ''"):
            await async_client.batch.with_raw_response.retrieve_job_status(
                job_id="",
                batch_id="batch_id",
            )

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_method_retrieve_patch_batch_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        batch = await async_client.batch.retrieve_patch_batch_status(
            patch_batch_idx=0,
            batch_id="batch_id",
            job_id="job_id",
        )
        assert_matches_type(PatchBatchStatusInfo, batch, path=["response"])

    @pytest.mark.skip(reason="Prism tests are disabled")
    @parametrize
    async def test_path_params_retrieve_patch_batch_status(self, async_client: AsyncSpatialiseSoilPrediction) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `batch_id` but received ''"):
            await async_client.batch.with_raw_response.retrieve_patch_batch_status(
                patch_batch_idx=0,
                batch_id="",
                job_id="job_id",
            )

        with pytest.raises(ValueError, match=r"Expected a non-empty value for `job_id` but received ''"):
            await async_client.batch.with_raw_response.retrieve_patch_batch_status(
                patch_batch_idx=0,
                batch_id="batch_id",
                job_id="",
            )


class TestBatchCountFieldAliases:
    """The API serializes counts as ``*_tasks``; the SDK exposes ``*_jobs`` (alias)
    plus ``*_tasks`` properties. Both must resolve from a wire ``*_tasks`` payload.
    """

    def test_create_response_total_tasks_alias(self) -> None:
        resp = BatchCreateResponse.construct(
            batch_id="b",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            job_ids={},
            message="ok",
            status="created",
            total_tasks=3,
        )
        assert resp.total_jobs == 3
        assert resp.total_tasks == 3

    def test_status_response_count_aliases(self) -> None:
        resp = BatchRetrieveStatusResponse.construct(
            batch_id="b",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status="processing",
            jobs=[],
            has_more=False,
            total_tasks=5,
            completed_tasks=2,
            failed_tasks=0,
            pending_tasks=3,
        )
        # historical *_jobs names keep working
        assert (resp.total_jobs, resp.completed_jobs, resp.failed_jobs, resp.pending_jobs) == (5, 2, 0, 3)
        # wire-name properties resolve to the same values
        assert (resp.total_tasks, resp.completed_tasks, resp.failed_tasks, resp.pending_tasks) == (5, 2, 0, 3)


class TestBatchStatusDeserialization:
    """Exercise the SDK's real (non-validating) ``construct_type`` path used to
    build API responses (via ``cast_to=``), not the validating constructor.

    This is the path that catches a field rename / alias mismatch / dropped field,
    so it deserializes a raw wire dict end to end.
    """

    def test_deserializes_wire_payload_with_task_counts_and_nested_job(self) -> None:
        wire: dict[str, object] = {
            "batch_id": "batch-1",
            "status": "processing",
            "total_tasks": 4,
            "completed_tasks": 1,
            "failed_tasks": 0,
            "pending_tasks": 3,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:05:00Z",
            "has_more": False,
            "next_cursor": None,
            "jobs": [
                {
                    "job_id": "job-1",
                    "status": "running",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:05:00Z",
                    "signed_cog_url": None,
                }
            ],
        }
        resp = cast(BatchRetrieveStatusResponse, construct_type(value=wire, type_=BatchRetrieveStatusResponse))
        # *_tasks wire keys land on the aliased *_jobs attributes (and *_tasks props)
        assert resp.total_jobs == 4 and resp.total_tasks == 4
        assert resp.completed_jobs == 1 and resp.pending_jobs == 3
        # nested job deserializes through the same path
        assert len(resp.jobs) == 1
        assert resp.jobs[0].job_id == "job-1"
        assert resp.jobs[0].status == "running"
        assert resp.jobs[0].signed_cog_url is None

    def test_deserializes_when_count_keys_absent(self) -> None:
        # A payload missing the count keys must not raise during construction;
        # the absent counts simply don't populate (the real path is non-validating).
        wire: dict[str, object] = {
            "batch_id": "batch-2",
            "status": "created",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "has_more": False,
            "jobs": [],
        }
        resp = cast(BatchRetrieveStatusResponse, construct_type(value=wire, type_=BatchRetrieveStatusResponse))
        assert resp.batch_id == "batch-2"
        assert resp.jobs == []


class TestJobDetailStatus:
    """Model-level coverage for the V2 job-detail / patch-batch status surface."""

    def test_job_mid_progress(self) -> None:
        resp = JobDetailStatusResponse.construct(
            job_id="job-mid",
            status="running",
            created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
            total_patch_batches=8,
            completed_patch_batches=3,
            has_more=True,
            next_cursor="cursor",
            patch_batches=[
                PatchBatchStatusInfo.construct(
                    patch_batch_idx=0,
                    status="completed",
                    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    point_count=128,
                    inference_duration_ms=4200,
                ),
                PatchBatchStatusInfo.construct(
                    patch_batch_idx=1,
                    status="running",
                    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                ),
            ],
        )
        assert resp.completed_patch_batches == 3
        assert resp.total_patch_batches == 8
        assert len(resp.patch_batches) == 2
        assert resp.patch_batches[0].patch_batch_idx == 0
        assert resp.has_more is True
        assert resp.next_cursor == "cursor"

    def test_job_fully_complete(self) -> None:
        resp = JobDetailStatusResponse.construct(
            job_id="job-done",
            status="completed",
            created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            total_patch_batches=8,
            completed_patch_batches=8,
            signed_cog_url="https://example.com/cog.tif",
            has_more=False,
            patch_batches=[],
        )
        assert resp.completed_patch_batches == resp.total_patch_batches == 8
        assert resp.signed_cog_url == "https://example.com/cog.tif"
        assert resp.has_more is False


class TestPatchBatchStatus:
    """Model-level coverage for a single patch-batch status."""

    def test_running_patch_batch(self) -> None:
        pb = PatchBatchStatusInfo.construct(
            patch_batch_idx=2,
            status="running",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            point_count=64,
        )
        assert pb.patch_batch_idx == 2
        assert pb.status == "running"
        assert pb.point_count == 64
        assert pb.failure_reason is None

    def test_failed_patch_batch(self) -> None:
        pb = PatchBatchStatusInfo.construct(
            patch_batch_idx=3,
            status="failed",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            failure_reason="inference timeout",
        )
        assert pb.status == "failed"
        assert pb.failure_reason == "inference timeout"

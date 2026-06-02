# This file is part of the spatialise SDK and is maintained by hand.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from spatialise import SpatialiseSoilPrediction, AsyncSpatialiseSoilPrediction
from tests.utils import assert_matches_type
from spatialise.types import (
    BatchCreateResponse,
    BatchRetrieveStatusResponse,
)
from spatialise.types.batch_retrieve_status_response import Job

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


class TestJobPatchBatchProgress:
    """Model-level coverage for the additive per-job patch-batch progress fields.

    These run without a Prism mock: they construct ``Job`` directly and assert the
    new optional fields round-trip and stay backward compatible (default ``None``).
    """

    def test_job_mid_progress(self) -> None:
        job = Job(
            job_id="job-mid",
            status="running",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:05:00Z",
            total_patch_batches=8,
            completed_patch_batches=3,
        )
        assert job.total_patch_batches == 8
        assert job.completed_patch_batches == 3
        # existing fields keep their meaning
        assert job.status == "running"
        assert job.signed_cog_url is None

    def test_job_fully_complete(self) -> None:
        job = Job(
            job_id="job-done",
            status="completed",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T01:00:00Z",
            total_patch_batches=8,
            completed_patch_batches=8,
            signed_cog_url="https://example.com/cog.tif",
        )
        assert job.completed_patch_batches == job.total_patch_batches == 8
        assert job.signed_cog_url == "https://example.com/cog.tif"

    def test_job_patch_batch_fields_default_none(self) -> None:
        # 0.2.x payloads omit the new fields entirely; they must default to None.
        job = Job(
            job_id="job-legacy",
            status="pending",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert job.total_patch_batches is None
        assert job.completed_patch_batches is None

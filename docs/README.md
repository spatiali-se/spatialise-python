# Spatialise Soil Prediction Python API library

<!-- prettier-ignore -->
[![PyPI version](https://img.shields.io/pypi/v/spatialise.svg?label=pypi%20(stable))](https://pypi.org/project/spatialise/)

The Spatialise Soil Prediction Python library provides convenient access to the Spatialise Soil Prediction REST API from any Python 3.8+ application. The library includes type definitions for all request params and response fields, and offers both synchronous and asynchronous clients powered by [httpx](https://github.com/encode/httpx).

> **New in v0.3.0:** target the V2 API with `version="v2"` and track per-job
> progress with `retrieve_job_status` / `retrieve_patch_batch_status`. See
> [What's new in v0.3.0](whats-new-v0.3.0.md) for the full list and migration notes.

## Installation

```sh
pip install --pre spatialise
```

## Quick Start

Get started with soil organic carbon predictions in under 5 minutes:

```python
import os
from spatialise import SpatialiseSoilPrediction

# Best practice: Load API key from environment variables
api_key = os.environ.get("SPATIALISE_API_KEY")
if not api_key:
    raise ValueError(
        "SPATIALISE_API_KEY environment variable not set. "
        "Get your API key from https://spatialise.dev"
    )

# Initialize the client
client = SpatialiseSoilPrediction(api_key=api_key)

# Submit a batch of soil prediction jobs
try:
    batch = client.batch.create(
        jobs=[
            {
                "year": 2021,
                "polygon": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [6.7, 52.8],
                            [6.70074, 52.8],
                            [6.70074, 52.80045],
                            [6.7, 52.80045],
                            [6.7, 52.8],
                        ]
                    ],
                },
            }
        ],
        metadata={
            "project": "Quick Start Example",
            "location": "Netherlands",
        },
    )

    print(f"Batch submitted successfully!")
    print(f"  Batch ID: {batch.batch_id}")
    print(f"  Status: {batch.status}")
    print(f"  Total jobs: {batch.total_jobs}")

except Exception as e:
    print(f"Error: {e}")
```

**Next steps:** Use the batch ID to [check status](#checking-batch-status) or set up [webhooks](#using-webhooks-for-notifications) for automatic notifications.

## Common Tasks

### Checking Batch Status

Check the status of your batch and retrieve results:

```python
# Get batch status
status = client.batch.retrieve_status(batch_id="batch_abc123")

print(f"Batch {status.batch_id}: {status.status}")
print(f"Progress: {status.completed_jobs}/{status.total_jobs} jobs completed")

# Access individual job results
for job in status.jobs:
    if job.status == "completed":
        print(f"  Job {job.job_id}: {job.signed_cog_url}")
    elif job.status == "failed":
        print(f"  FAILED Job {job.job_id}: {job.error_message}")
```

Each count is also available under its wire name (`status.total_tasks`,
`status.completed_tasks`, ...); the `*_jobs` names above are kept as aliases and
return the same values.

### Inspecting Per-Job Patch-Batch Progress (V2)

On the V2 pipeline each job is processed as several **patch-batches**. The
job-detail endpoint surfaces this fan-in so you can show fine-grained progress
before a job's COG is ready:

```python
# Drill into a single job's patch-batch progress
detail = client.batch.retrieve_job_status(job_id="job_xyz", batch_id="batch_abc123")

if detail.total_patch_batches:
    done = detail.completed_patch_batches or 0
    print(f"Job {detail.job_id}: {done}/{detail.total_patch_batches} patch-batches")

# Iterate the (paginated) per-patch-batch statuses
for pb in detail.patch_batches:
    print(f"  patch-batch {pb.patch_batch_idx}: {pb.status}")
    if pb.status == "failed":
        print(f"    failed: {pb.failure_reason}")

# Fetch the next page of patch-batches when there are more
if detail.has_more:
    next_page = client.batch.retrieve_job_status(
        job_id="job_xyz", batch_id="batch_abc123", cursor=detail.next_cursor
    )
```

Inspect a single patch-batch directly by its index:

```python
pb = client.batch.retrieve_patch_batch_status(
    patch_batch_idx=0, batch_id="batch_abc123", job_id="job_xyz"
)
print(f"patch-batch {pb.patch_batch_idx}: {pb.status}, {pb.point_count} points")
```

> These endpoints return useful data only when pointed at a V2 deployment. A
> client targeting the v1 host (via `base_url`) keeps working unchanged and
> simply does not call them.

### Polling Until Completion

Poll for batch completion with proper timing and error handling:

```python
import time
from spatialise import SpatialiseSoilPrediction

client = SpatialiseSoilPrediction()

def wait_for_batch(batch_id: str, timeout: int = 600, poll_interval: int = 10):
    """
    Poll batch status until completion or timeout.

    Args:
        batch_id: The batch ID to monitor
        timeout: Maximum time to wait in seconds (default: 10 minutes)
        poll_interval: Time between status checks in seconds (default: 10s)

    Returns:
        Final batch status response
    """
    start_time = time.time()

    while True:
        # Check if we've exceeded timeout
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Batch {batch_id} did not complete within {timeout}s")

        # Get current status
        status = client.batch.retrieve_status(batch_id)

        # Check for terminal states
        if status.status == "completed":
            print(f"Batch completed: {status.completed_jobs} jobs successful")
            return status
        elif status.status == "failed":
            print(f"Batch failed: {status.failed_jobs} jobs failed")
            return status

        # Still processing - wait before next check
        print(f"  Processing: {status.completed_jobs}/{status.total_jobs} completed...")
        time.sleep(poll_interval)

# Usage
batch = client.batch.create(jobs=[...])
final_status = wait_for_batch(batch.batch_id)
```

### Using Webhooks for Notifications

Instead of polling, receive automatic notifications when your batch completes:

```python
# Create batch with webhook configuration
batch = client.batch.create(
    jobs=[...],
    webhook_url="https://your-domain.com/webhooks/spatialise",
    webhook_secret="your-secret-key-here",
)

print(f"Batch {batch.batch_id} created with webhook notification")
```

When the batch completes, Spatialise will POST to your webhook URL with the results. The request includes an `X-Spatialise-Signature` header for authentication.

**Complete webhook examples:**
- [FastAPI webhook handler](https://github.com/spatiali-se/spatialise-python/tree/development/examples/webhook_handler_fastapi.py) - Production-ready with signature verification
- [Flask webhook handler](https://github.com/spatiali-se/spatialise-python/tree/development/examples/webhook_handler_flask.py) - Simple Flask implementation
- [Creating batches with webhooks](https://github.com/spatiali-se/spatialise-python/tree/development/examples/batch_prediction_webhook.py) - Full workflow example

### Handling Paginated Results

When retrieving status for batches with many jobs, results are paginated:

```python
def get_all_jobs(batch_id: str):
    """Retrieve all jobs from a batch, handling pagination."""
    all_jobs = []
    cursor = None

    while True:
        # Fetch page of results
        response = client.batch.retrieve_status(
            batch_id=batch_id,
            limit=100,  # Max 100 jobs per page
            cursor=cursor,
        )

        all_jobs.extend(response.jobs)

        # Check if there are more pages
        if not response.next_cursor:
            break

        cursor = response.next_cursor

    return all_jobs

# Usage
all_jobs = get_all_jobs("batch_abc123")
print(f"Retrieved {len(all_jobs)} total jobs")
```

### Error Handling and Recovery

Handle API errors gracefully with specific exception handling:

```python
import spatialise
from spatialise import SpatialiseSoilPrediction

client = SpatialiseSoilPrediction()

try:
    batch = client.batch.create(jobs=[...])

except spatialise.AuthenticationError:
    print("Invalid API key. Check your SPATIALISE_API_KEY")

except spatialise.RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.response.headers.get('Retry-After')}s")
    # Implement exponential backoff here

except spatialise.BadRequestError as e:
    print(f"Invalid request: {e.message}")
    print(f"   Status: {e.status_code}")
    # Log error details for debugging

except spatialise.APIConnectionError as e:
    print(f"Network error: {e.__cause__}")
    # Retry with exponential backoff

except spatialise.APIStatusError as e:
    print(f"API error {e.status_code}: {e.message}")
    # Log and alert for investigation
```

**Error hierarchy:**
- `APIError` - Base class for all API errors
- `APIConnectionError` - Network/connection issues
- `APIStatusError` - Non-2xx HTTP responses
  - `BadRequestError` (400)
  - `AuthenticationError` (401)
  - `PermissionDeniedError` (403)
  - `NotFoundError` (404)
  - `UnprocessableEntityError` (422)
  - `RateLimitError` (429)
  - `InternalServerError` (500+)

### Using the Async Client

For high-concurrency workloads, use `AsyncSpatialiseSoilPrediction`:

```python
import asyncio
from spatialise import AsyncSpatialiseSoilPrediction

async def main():
    client = AsyncSpatialiseSoilPrediction()

    # Submit batch asynchronously
    batch = await client.batch.create(
        jobs=[
            {
                "year": 2021,
                "polygon": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [6.7, 52.8],
                            [6.70074, 52.8],
                            [6.70074, 52.80045],
                            [6.7, 52.80045],
                            [6.7, 52.8],
                        ]
                    ],
                },
            }
        ]
    )

    print(f"Batch ID: {batch.batch_id}")

    # Check status asynchronously
    status = await client.batch.retrieve_status(batch.batch_id)
    print(f"Status: {status.status}")

asyncio.run(main())
```

**Performance boost with aiohttp:**

```sh
pip install --pre spatialise[aiohttp]
```

```python
from spatialise import AsyncSpatialiseSoilPrediction, DefaultAioHttpClient

async with AsyncSpatialiseSoilPrediction(
    http_client=DefaultAioHttpClient()
) as client:
    batch = await client.batch.create(jobs=[...])
```

## Advanced Guides

For comprehensive documentation on specific advanced topics:

- **[Webhook Integration](./webhooks.md)** - HMAC signature verification, security best practices, and production deployment patterns for webhook handlers
- **[Idempotency](./idempotency.md)** - Preventing duplicate operations using idempotency keys with implementation patterns for retries and database-backed idempotency
- **[Rate Limiting](./rate-limiting.md)** - Understanding API rate limits, implementing exponential backoff, and request throttling strategies
- **[Production Patterns](./production-patterns.md)** - Secret management, database integration, async processing with Celery/SQS, logging, monitoring, and error recovery
- **[GeoTIFF Processing](./geotiff-processing.md)** - Downloading, processing, and visualizing soil prediction results using Rasterio

## Advanced Features

### Configuring Retries

Customize retry behavior for failed requests:

```python
from spatialise import SpatialiseSoilPrediction

# Configure default retries for all requests
client = SpatialiseSoilPrediction(
    max_retries=5,  # Default is 2
)

# Or configure per-request
client.with_options(max_retries=0).batch.create(jobs=[...])
```

By default, the following errors are retried with exponential backoff:
- Connection errors (network issues)
- 408 Request Timeout
- 409 Conflict
- 429 Rate Limit
- 500+ Internal Server Errors

### Configuring Timeouts

Set request timeout limits:

```python
import httpx
from spatialise import SpatialiseSoilPrediction

# Simple timeout (in seconds)
client = SpatialiseSoilPrediction(timeout=20.0)

# Granular timeout control
client = SpatialiseSoilPrediction(
    timeout=httpx.Timeout(
        connect=5.0,   # Time to establish connection
        read=10.0,     # Time to read response
        write=10.0,    # Time to write request
        pool=5.0,      # Time to acquire connection from pool
    )
)

# Per-request timeout override
client.with_options(timeout=30.0).batch.create(jobs=[...])
```

### Accessing Raw Response Data

Access HTTP headers and raw response data:

```python
from spatialise import SpatialiseSoilPrediction

client = SpatialiseSoilPrediction()

# Get raw response object
response = client.batch.with_raw_response.create(jobs=[...])

print(f"Rate limit remaining: {response.headers.get('X-RateLimit-Remaining')}")
print(f"Request ID: {response.headers.get('X-Request-ID')}")

# Parse response body
batch = response.parse()
print(f"Batch ID: {batch.batch_id}")
```

### Streaming Responses

Stream large responses without loading entire body into memory:

```python
with client.batch.with_streaming_response.create(jobs=[...]) as response:
    print(f"Request ID: {response.headers.get('X-Request-ID')}")

    # Stream response body
    for chunk in response.iter_bytes():
        # Process chunk
        pass
```

### Custom HTTP Client Configuration

Customize the underlying HTTP client for proxies, custom transports, etc.:

```python
import httpx
from spatialise import SpatialiseSoilPrediction, DefaultHttpxClient

client = SpatialiseSoilPrediction(
    http_client=DefaultHttpxClient(
        proxy="http://proxy.example.com:8080",
        transport=httpx.HTTPTransport(local_address="0.0.0.0"),
    )
)
```

### Type Safety and IDE Support

All request parameters use TypedDicts and responses are Pydantic models:

```python
from spatialise.types import BatchCreateParams

# Type-safe request parameters
params: BatchCreateParams = {
    "jobs": [
        {
            "year": 2021,
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[6.7, 52.8], [6.70074, 52.8], ...]],
            },
        }
    ],
    "metadata": {"project": "Analysis"},
}

batch = client.batch.create(**params)

# Pydantic model methods
batch_json = batch.to_json()  # Serialize to JSON
batch_dict = batch.to_dict()  # Convert to dictionary
```

For type checking in VS Code, set `python.analysis.typeCheckingMode` to `basic`.

## API Reference

For complete API documentation including all methods, parameters, and return types:

- **[What's new in v0.3.0](whats-new-v0.3.0.md)** - V2 support, new methods, and migration notes
- **[Example Scripts](https://github.com/spatiali-se/spatialise-python/tree/development/examples)** - Working code examples for common workflows
- **[Type Definitions](https://github.com/spatiali-se/spatialise-python/tree/development/src/spatialise/types)** - Request and response type definitions

## Configuration

### API Key

Set your API key via environment variable (recommended):

```bash
export SPATIALISE_API_KEY='your-api-key-here'
```

Or pass directly to the client:

```python
client = SpatialiseSoilPrediction(api_key="your-api-key-here")
```

### Base URL

Override the API base URL (useful for testing):

```bash
export SPATIALISE_SOIL_PREDICTION_BASE_URL='https://custom.api.example.com'
```

### Logging

Enable debug logging:

```bash
export SPATIALISE_SOIL_PREDICTION_LOG=debug
```

Or in Python:

```python
import logging
logging.getLogger("spatialise").setLevel(logging.DEBUG)
```

## Requirements

Python 3.8 or higher.

## Versioning

This package follows [SemVer](https://semver.org/spec/v2.0.0.html) conventions, though certain backwards-incompatible changes may be released as minor versions:

1. Changes that only affect static types, without breaking runtime behavior
2. Changes to library internals which are technically public but not intended or documented for external use
3. Changes that we do not expect to impact the vast majority of users in practice

We take backwards-compatibility seriously and work hard to ensure you can rely on a smooth upgrade experience.

**Check your installed version:**

```python
import spatialise
print(spatialise.__version__)
```

## Contributing

See [the contributing documentation](https://github.com/spatiali-se/spatialise-python/blob/development/CONTRIBUTING.md).

## Support

- **Issues:** [GitHub Issues](https://www.github.com/spatiali-se/spatialise-python/issues)
- **Documentation:** [What's new in v0.3.0](whats-new-v0.3.0.md)
- **Examples:** [Example Scripts](https://github.com/spatiali-se/spatialise-python/tree/development/examples)

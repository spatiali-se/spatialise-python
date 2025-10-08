# Rate Limiting

This guide explains the Spatialise API rate limits, detection strategies, and implementation patterns for handling rate limit errors with exponential backoff and request throttling.

## Overview

The Spatialise API implements rate limiting to ensure fair resource allocation and system stability. Rate limits are enforced per API key with daily quotas based on computational resources consumed.

### Rate Limit Structure

| Resource | Limit | Period | Scope |
|----------|-------|--------|-------|
| Total hectares | 5,000 ha | 24 hours | Per API key |
| Total jobs | 1,000 jobs | 24 hours | Per API key |

Limits reset at 00:00 UTC daily.

### Quota Calculation

Each batch submission consumes quota based on:

```python
# Job quota: Each job counts as 1 regardless of size
job_quota = len(jobs)

# Hectare quota: Sum of all polygon areas
hectare_quota = sum(calculate_area_hectares(job['polygon']) for job in jobs)
```

Example:
```python
batch = client.batch.create(
    jobs=[
        {"year": 2021, "polygon": polygon_100ha},  # 100 hectares
        {"year": 2021, "polygon": polygon_50ha},   # 50 hectares
    ]
)
# Consumes: 2 jobs, 150 hectares
```

## Rate Limit Headers

The API includes rate limit information in response headers:

```
X-RateLimit-Limit-Jobs: 1000
X-RateLimit-Remaining-Jobs: 847
X-RateLimit-Reset-Jobs: 1642291200

X-RateLimit-Limit-Hectares: 5000
X-RateLimit-Remaining-Hectares: 3250
X-RateLimit-Reset-Hectares: 1642291200
```

### Reading Rate Limit Headers

```python
from spatialise import SpatialiseSoilPrediction

client = SpatialiseSoilPrediction()

response = client.batch.with_raw_response.create(jobs=[...])

# Parse rate limit headers
jobs_remaining = int(response.headers.get('X-RateLimit-Remaining-Jobs', 0))
hectares_remaining = int(response.headers.get('X-RateLimit-Remaining-Hectares', 0))
reset_time = int(response.headers.get('X-RateLimit-Reset-Jobs', 0))

print(f"Remaining quota: {jobs_remaining} jobs, {hectares_remaining} hectares")
print(f"Resets at: {datetime.fromtimestamp(reset_time)}")

# Access the parsed response
batch = response.parse()
```

## Handling Rate Limit Errors

### Detecting Rate Limits

When rate limits are exceeded, the API returns HTTP 429:

```python
import spatialise

try:
    batch = client.batch.create(jobs=[...])
except spatialise.RateLimitError as e:
    print(f"Rate limit exceeded: {e.message}")
    print(f"Status code: {e.status_code}")

    # Extract retry information
    retry_after = e.response.headers.get('Retry-After')
    if retry_after:
        print(f"Retry after {retry_after} seconds")
```

### Retry-After Header

The `Retry-After` header indicates when to retry:

```python
import time
import spatialise

def create_batch_with_rate_limit_retry(client, jobs, metadata=None):
    """Create batch with rate limit retry."""
    try:
        return client.batch.create(jobs=jobs, metadata=metadata)
    except spatialise.RateLimitError as e:
        retry_after = e.response.headers.get('Retry-After')
        if retry_after:
            wait_seconds = int(retry_after)
            print(f"Rate limited. Waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)
            return client.batch.create(jobs=jobs, metadata=metadata)
        raise
```

## Exponential Backoff

Exponential backoff gradually increases wait time between retries to reduce server load.

### Basic Implementation

```python
import time
import spatialise

def create_batch_with_backoff(client, jobs, metadata=None, max_retries=5):
    """Create batch with exponential backoff on rate limits."""
    base_delay = 1  # Start with 1 second

    for attempt in range(max_retries):
        try:
            return client.batch.create(jobs=jobs, metadata=metadata)
        except spatialise.RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            # Check for Retry-After header first
            retry_after = e.response.headers.get('Retry-After')
            if retry_after:
                wait_time = int(retry_after)
            else:
                # Exponential backoff: 1, 2, 4, 8, 16 seconds
                wait_time = min(base_delay * (2 ** attempt), 60)

            print(f"Rate limited on attempt {attempt + 1}. "
                  f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
```

### Exponential Backoff with Jitter

Add randomization to prevent thundering herd problem:

```python
import random
import time
import spatialise

def create_batch_with_jittered_backoff(
    client,
    jobs,
    metadata=None,
    max_retries=5,
    base_delay=1,
    max_delay=60
):
    """Create batch with jittered exponential backoff.

    Parameters
    ----------
    client : SpatialiseSoilPrediction
        The API client instance.
    jobs : list
        List of prediction jobs.
    metadata : dict, optional
        Batch metadata.
    max_retries : int, default=5
        Maximum number of retry attempts.
    base_delay : float, default=1
        Base delay in seconds for exponential backoff.
    max_delay : float, default=60
        Maximum delay in seconds.

    Returns
    -------
    BatchCreateResponse
        The created batch.

    Raises
    ------
    RateLimitError
        If rate limit is still exceeded after max_retries.
    """
    for attempt in range(max_retries):
        try:
            return client.batch.create(jobs=jobs, metadata=metadata)
        except spatialise.RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            # Use Retry-After if provided
            retry_after = e.response.headers.get('Retry-After')
            if retry_after:
                wait_time = int(retry_after)
            else:
                # Exponential backoff with jitter
                exponential_delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, exponential_delay * 0.1)
                wait_time = exponential_delay + jitter

            time.sleep(wait_time)
```

## Request Throttling

Prevent rate limits by throttling request rate.

### Token Bucket Rate Limiter

Implement client-side rate limiting using token bucket algorithm:

```python
import time
import threading

class TokenBucket:
    """Token bucket rate limiter.

    Parameters
    ----------
    rate : float
        Tokens added per second.
    capacity : int
        Maximum bucket capacity.
    """

    def __init__(self, rate, capacity):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens=1):
        """Consume tokens, blocking if insufficient tokens available.

        Parameters
        ----------
        tokens : int, default=1
            Number of tokens to consume.

        Returns
        -------
        bool
            True if tokens were consumed.
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            # Wait for sufficient tokens
            wait_time = (tokens - self.tokens) / self.rate
            time.sleep(wait_time)

            self.tokens = 0
            self.last_update = time.time()
            return True


class ThrottledBatchClient:
    """Batch client with automatic rate throttling.

    Parameters
    ----------
    client : SpatialiseSoilPrediction
        The API client.
    jobs_per_day : int, default=1000
        Daily job quota.
    hectares_per_day : int, default=5000
        Daily hectare quota.
    """

    def __init__(self, client, jobs_per_day=1000, hectares_per_day=5000):
        self.client = client

        # Convert daily limits to per-second rates
        seconds_per_day = 86400
        self.job_limiter = TokenBucket(
            rate=jobs_per_day / seconds_per_day,
            capacity=jobs_per_day
        )
        self.hectare_limiter = TokenBucket(
            rate=hectares_per_day / seconds_per_day,
            capacity=hectares_per_day
        )

    def create_batch(self, jobs, metadata=None):
        """Create batch with automatic throttling.

        Parameters
        ----------
        jobs : list
            List of prediction jobs.
        metadata : dict, optional
            Batch metadata.

        Returns
        -------
        BatchCreateResponse
            The created batch.
        """
        job_count = len(jobs)

        # Estimate hectares (simplified - actual calculation more complex)
        estimated_hectares = job_count * 5  # Assume 5 ha per job

        # Consume tokens (blocks if insufficient)
        self.job_limiter.consume(job_count)
        self.hectare_limiter.consume(estimated_hectares)

        # Make request
        return self.client.batch.create(jobs=jobs, metadata=metadata)
```

Usage:

```python
client = SpatialiseSoilPrediction()
throttled_client = ThrottledBatchClient(client)

# Automatically throttled to stay within limits
for batch_jobs in job_batches:
    batch = throttled_client.create_batch(batch_jobs)
    print(f"Created batch: {batch.batch_id}")
```

### Sliding Window Rate Limiter

Track requests over a sliding time window:

```python
from collections import deque
import time

class SlidingWindowRateLimiter:
    """Sliding window rate limiter.

    Parameters
    ----------
    max_requests : int
        Maximum requests in window.
    window_seconds : float
        Window duration in seconds.
    """

    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()

    def acquire(self):
        """Acquire permission to make request, blocking if necessary."""
        with self.lock:
            now = time.time()

            # Remove requests outside window
            cutoff = now - self.window_seconds
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            # Wait until oldest request expires
            wait_time = self.requests[0] + self.window_seconds - now
            if wait_time > 0:
                time.sleep(wait_time)

            self.requests.append(time.time())
            return True


# Usage
limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=3600)

for batch_jobs in job_batches:
    limiter.acquire()
    batch = client.batch.create(jobs=batch_jobs)
```

## Batching Strategies

Optimize quota usage by batching requests efficiently.

### Adaptive Batch Sizing

Adjust batch size based on remaining quota:

```python
def create_batches_with_quota_awareness(client, all_jobs, max_batch_size=100):
    """Create batches while monitoring quota.

    Parameters
    ----------
    client : SpatialiseSoilPrediction
        The API client.
    all_jobs : list
        All jobs to process.
    max_batch_size : int, default=100
        Maximum jobs per batch.

    Yields
    ------
    BatchCreateResponse
        Created batches.
    """
    remaining = all_jobs[:]

    while remaining:
        # Get current quota
        response = client.batch.with_raw_response.create(
            jobs=remaining[:1]  # Probe with single job
        )
        batch = response.parse()

        jobs_remaining = int(
            response.headers.get('X-RateLimit-Remaining-Jobs', max_batch_size)
        )

        # Determine batch size
        batch_size = min(len(remaining), jobs_remaining, max_batch_size)

        if batch_size == 0:
            # Wait for quota reset
            reset_time = int(response.headers.get('X-RateLimit-Reset-Jobs', 0))
            wait_time = max(reset_time - time.time(), 0)
            print(f"Quota exhausted. Waiting {wait_time}s for reset...")
            time.sleep(wait_time)
            continue

        # Submit batch
        batch_jobs = remaining[:batch_size]
        try:
            batch = client.batch.create(jobs=batch_jobs)
            yield batch
            remaining = remaining[batch_size:]
        except spatialise.RateLimitError:
            # Reduce batch size and retry
            batch_size = max(1, batch_size // 2)
            continue
```

### Priority-Based Scheduling

Process high-priority jobs first when quota is limited:

```python
from dataclasses import dataclass
from typing import List
import heapq

@dataclass
class PrioritizedJob:
    priority: int
    job: dict

    def __lt__(self, other):
        return self.priority < other.priority


class PriorityBatchScheduler:
    """Schedule batch jobs by priority with quota awareness."""

    def __init__(self, client):
        self.client = client
        self.queue = []

    def add_job(self, job, priority=0):
        """Add job to priority queue.

        Parameters
        ----------
        job : dict
            Job specification.
        priority : int, default=0
            Job priority (lower number = higher priority).
        """
        heapq.heappush(self.queue, PrioritizedJob(priority, job))

    def process_queue(self, batch_size=100):
        """Process jobs in priority order.

        Parameters
        ----------
        batch_size : int, default=100
            Maximum jobs per batch.

        Yields
        ------
        BatchCreateResponse
            Created batches.
        """
        while self.queue:
            # Collect highest priority jobs
            batch_jobs = []
            while self.queue and len(batch_jobs) < batch_size:
                prioritized_job = heapq.heappop(self.queue)
                batch_jobs.append(prioritized_job.job)

            # Submit batch with retry
            try:
                batch = client.batch.create(jobs=batch_jobs)
                yield batch
            except spatialise.RateLimitError as e:
                # Re-queue jobs for later
                for job in batch_jobs:
                    self.add_job(job, priority=0)

                # Wait before retry
                retry_after = int(e.response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
```

## Monitoring and Alerting

Track quota usage to prevent unexpected rate limits.

### Quota Tracking

```python
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class QuotaSnapshot:
    """Quota usage snapshot."""
    timestamp: datetime
    jobs_remaining: int
    hectares_remaining: int
    jobs_limit: int
    hectares_limit: int

    @property
    def jobs_used_percent(self):
        return 100 * (1 - self.jobs_remaining / self.jobs_limit)

    @property
    def hectares_used_percent(self):
        return 100 * (1 - self.hectares_remaining / self.hectares_limit)


class QuotaMonitor:
    """Monitor API quota usage."""

    def __init__(self, client, warning_threshold=0.8):
        self.client = client
        self.warning_threshold = warning_threshold
        self.snapshots = []

    def record_request(self, response):
        """Record quota usage from API response.

        Parameters
        ----------
        response : APIResponse
            Raw API response with headers.
        """
        snapshot = QuotaSnapshot(
            timestamp=datetime.utcnow(),
            jobs_remaining=int(response.headers.get('X-RateLimit-Remaining-Jobs', 0)),
            hectares_remaining=int(response.headers.get('X-RateLimit-Remaining-Hectares', 0)),
            jobs_limit=int(response.headers.get('X-RateLimit-Limit-Jobs', 1000)),
            hectares_limit=int(response.headers.get('X-RateLimit-Limit-Hectares', 5000))
        )

        self.snapshots.append(snapshot)

        # Check thresholds
        if snapshot.jobs_used_percent > self.warning_threshold * 100:
            logger.warning(
                f"Job quota at {snapshot.jobs_used_percent:.1f}%: "
                f"{snapshot.jobs_remaining} / {snapshot.jobs_limit} remaining"
            )

        if snapshot.hectares_used_percent > self.warning_threshold * 100:
            logger.warning(
                f"Hectare quota at {snapshot.hectares_used_percent:.1f}%: "
                f"{snapshot.hectares_remaining} / {snapshot.hectares_limit} remaining"
            )

        return snapshot

    def create_batch_monitored(self, jobs, metadata=None):
        """Create batch with quota monitoring.

        Parameters
        ----------
        jobs : list
            List of prediction jobs.
        metadata : dict, optional
            Batch metadata.

        Returns
        -------
        tuple
            (batch, quota_snapshot)
        """
        response = self.client.batch.with_raw_response.create(
            jobs=jobs,
            metadata=metadata
        )

        snapshot = self.record_request(response)
        batch = response.parse()

        return batch, snapshot
```

Usage:

```python
client = SpatialiseSoilPrediction()
monitor = QuotaMonitor(client, warning_threshold=0.8)

batch, quota = monitor.create_batch_monitored(jobs=[...])
print(f"Jobs quota: {quota.jobs_used_percent:.1f}% used")
print(f"Hectares quota: {quota.hectares_used_percent:.1f}% used")
```

## Best Practices

### Always Implement Retry Logic

Production code should handle rate limits gracefully:

```python
def robust_batch_create(client, jobs, metadata=None):
    """Create batch with production-grade error handling."""
    max_retries = 5

    for attempt in range(max_retries):
        try:
            return client.batch.create(jobs=jobs, metadata=metadata)
        except spatialise.RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            retry_after = int(e.response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
        except spatialise.APIConnectionError as e:
            if attempt == max_retries - 1:
                raise

            time.sleep(2 ** attempt)
```

### Monitor Quota Proactively

Check quota before submitting large batches:

```python
def check_quota_before_submit(client, required_jobs, required_hectares):
    """Verify sufficient quota before submission.

    Returns
    -------
    bool
        True if sufficient quota available.
    """
    # Make minimal request to check quota
    response = client.batch.with_raw_response.create(jobs=[...])  # Single test job

    jobs_remaining = int(response.headers.get('X-RateLimit-Remaining-Jobs', 0))
    hectares_remaining = int(response.headers.get('X-RateLimit-Remaining-Hectares', 0))

    return (jobs_remaining >= required_jobs and
            hectares_remaining >= required_hectares)
```

### Use Client Configuration

Configure retry behavior at client level:

```python
# Automatic retries for rate limits
client = SpatialiseSoilPrediction(max_retries=3)

# Client handles rate limits automatically
batch = client.batch.create(jobs=[...])
```

### Distribute Load Over Time

Avoid submitting all requests at start of quota period:

```python
import time

def distributed_batch_submission(client, job_batches, distribution_hours=24):
    """Distribute batch submissions over time period.

    Parameters
    ----------
    client : SpatialiseSoilPrediction
        API client.
    job_batches : list
        List of job batches to submit.
    distribution_hours : float, default=24
        Hours over which to distribute requests.

    Yields
    ------
    BatchCreateResponse
        Created batches.
    """
    interval = (distribution_hours * 3600) / len(job_batches)

    for batch_jobs in job_batches:
        batch = client.batch.create(jobs=batch_jobs)
        yield batch

        if batch_jobs != job_batches[-1]:  # Not last batch
            time.sleep(interval)
```

## See Also

- [Idempotency](./idempotency.md) - Safe request retries
- [Webhook Integration](./webhooks.md) - Avoid polling overhead
- [Production Patterns](./production-patterns.md) - Queue-based request management

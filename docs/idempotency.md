# Idempotency

This guide explains idempotent request handling in the Spatialise API, including key generation strategies, error handling, and implementation patterns for production systems.

## Overview

An idempotent operation produces the same result when executed multiple times with the same input. The Spatialise API supports idempotency through the `Idempotency-Key` header, allowing safe request retries without creating duplicate batches or incurring duplicate charges.

### Motivation

In distributed systems, requests may fail for various reasons:
- Network timeouts during response transmission
- Connection interruptions before receiving confirmation
- Server errors (5xx) with unclear processing state
- Client-side failures after successful server processing

Without idempotency, retrying these requests risks creating duplicate operations. With idempotency keys, the API guarantees that requests with the same key produce identical results.

## Basic Usage

Provide an idempotency key via the `extra_headers` parameter:

```python
from spatialise import SpatialiseSoilPrediction
import uuid

client = SpatialiseSoilPrediction()

idempotency_key = str(uuid.uuid4())

batch = client.batch.create(
    jobs=[...],
    extra_headers={"Idempotency-Key": idempotency_key}
)
```

The same key with identical request parameters will return the cached response:

```python
# Original request
batch1 = client.batch.create(
    jobs=[{"year": 2021, "polygon": {...}}],
    extra_headers={"Idempotency-Key": "key-123"}
)

# Retry with same key returns same batch
batch2 = client.batch.create(
    jobs=[{"year": 2021, "polygon": {...}}],
    extra_headers={"Idempotency-Key": "key-123"}
)

assert batch1.batch_id == batch2.batch_id
```

## Key Requirements

Idempotency keys must satisfy:

- **Uniqueness**: Different operations require different keys
- **Consistency**: Retries of the same operation must use the same key
- **Character set**: ASCII alphanumeric characters, hyphens, and underscores
- **Length**: Maximum 255 characters
- **Case sensitivity**: Keys are case-sensitive

## Key Generation Strategies

### UUID-Based Keys

Generate cryptographically random unique identifiers:

```python
import uuid

def create_batch_with_uuid_key(client, jobs, metadata=None):
    """Create batch with UUID-based idempotency key."""
    idempotency_key = str(uuid.uuid4())

    return client.batch.create(
        jobs=jobs,
        metadata=metadata,
        extra_headers={"Idempotency-Key": idempotency_key}
    )
```

**Advantages**: Guaranteed uniqueness, no collision risk
**Disadvantages**: Not human-readable, requires external storage for retry correlation

### Content-Based Keys

Derive keys from request content using cryptographic hashing:

```python
import hashlib
import json

def create_batch_with_content_key(client, jobs, metadata=None):
    """Create batch with content-derived idempotency key."""
    request_content = {
        "jobs": jobs,
        "metadata": metadata
    }

    content_json = json.dumps(request_content, sort_keys=True)
    content_hash = hashlib.sha256(content_json.encode()).hexdigest()
    idempotency_key = f"batch-{content_hash[:32]}"

    return client.batch.create(
        jobs=jobs,
        metadata=metadata,
        extra_headers={"Idempotency-Key": idempotency_key}
    )
```

**Advantages**: Automatic deduplication of identical requests
**Disadvantages**: Different requests with same desired outcome get different keys

### Business Logic Keys

Construct keys from domain identifiers:

```python
from datetime import date

def create_batch_with_business_key(
    client,
    project_id,
    date_str,
    run_number,
    jobs,
    metadata=None
):
    """Create batch with business logic-based idempotency key."""
    idempotency_key = f"{project_id}-{date_str}-run{run_number}"

    return client.batch.create(
        jobs=jobs,
        metadata=metadata,
        extra_headers={"Idempotency-Key": idempotency_key}
    )

# Usage
batch = create_batch_with_business_key(
    client,
    project_id="soil-analysis-2025",
    date_str=date.today().isoformat(),
    run_number=1,
    jobs=[...]
)
```

**Advantages**: Human-readable, debuggable, traceable
**Disadvantages**: Requires careful uniqueness management

## Key Lifecycle

### Storage and Expiration

The API stores idempotency keys with the following characteristics:

- **Time-to-live**: 24 hours from first request
- **Scope**: Per API key (keys are isolated between different API credentials)
- **Payload binding**: Keys are bound to the request payload hash

```python
import time

# Time T=0: Create batch
batch1 = client.batch.create(
    jobs=[...],
    extra_headers={"Idempotency-Key": "test-key"}
)

# Time T=1 hour: Retry returns cached response
batch2 = client.batch.create(
    jobs=[...],  # Same payload
    extra_headers={"Idempotency-Key": "test-key"}
)
assert batch1.batch_id == batch2.batch_id

# Time T=25 hours: Key expired, creates new batch
# (Do not use time.sleep in production for this duration)
batch3 = client.batch.create(
    jobs=[...],  # Same payload
    extra_headers={"Idempotency-Key": "test-key"}
)
assert batch3.batch_id != batch1.batch_id
```

### Payload Validation

The API validates that retry requests match the original payload:

```python
import spatialise

# Original request
batch1 = client.batch.create(
    jobs=[{"year": 2021, "polygon": polygon_a}],
    extra_headers={"Idempotency-Key": "key-123"}
)

# Modified request with same key raises error
try:
    batch2 = client.batch.create(
        jobs=[{"year": 2022, "polygon": polygon_b}],  # Different payload
        extra_headers={"Idempotency-Key": "key-123"}
    )
except spatialise.UnprocessableEntityError as e:
    if e.status_code == 409:
        print("Conflict: Same key with different payload")
```

## Error Handling

### Network Failures

Network failures during request/response indicate uncertain state. Retry with the same idempotency key:

```python
import spatialise
import time

def create_batch_with_retry(client, jobs, metadata=None, max_retries=3):
    """Create batch with automatic retry on network failures."""
    import uuid

    idempotency_key = str(uuid.uuid4())

    for attempt in range(max_retries):
        try:
            return client.batch.create(
                jobs=jobs,
                metadata=metadata,
                extra_headers={"Idempotency-Key": idempotency_key}
            )
        except spatialise.APIConnectionError as e:
            if attempt == max_retries - 1:
                raise

            backoff = min(2 ** attempt, 32)  # Cap at 32 seconds
            time.sleep(backoff)
```

### Conflict Errors (409)

HTTP 409 indicates idempotency key reuse with different payload:

```python
def handle_idempotency_conflict(client, jobs, metadata, idempotency_key):
    """Handle idempotency key conflicts."""
    try:
        return client.batch.create(
            jobs=jobs,
            metadata=metadata,
            extra_headers={"Idempotency-Key": idempotency_key}
        )
    except spatialise.UnprocessableEntityError as e:
        if e.status_code == 409:
            # Options:
            # 1. Generate new key and retry
            new_key = str(uuid.uuid4())
            return client.batch.create(
                jobs=jobs,
                metadata=metadata,
                extra_headers={"Idempotency-Key": new_key}
            )

            # 2. Fail and let caller handle
            # raise

            # 3. Fetch original batch if known
            # return client.batch.retrieve_status(original_batch_id)
        raise
```

### Server Errors (5xx)

Server errors with status codes 500-599 indicate transient failures. Retry with the same key:

```python
def create_batch_with_server_error_retry(client, jobs, metadata=None):
    """Create batch with retry on server errors."""
    import uuid

    idempotency_key = str(uuid.uuid4())
    max_retries = 3

    for attempt in range(max_retries):
        try:
            return client.batch.create(
                jobs=jobs,
                metadata=metadata,
                extra_headers={"Idempotency-Key": idempotency_key}
            )
        except spatialise.APIStatusError as e:
            # Retry server errors (5xx)
            if e.status_code >= 500:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            # Don't retry client errors (4xx)
            raise
```

## Implementation Patterns

### Pattern 1: Stateless Retry

Generate a new key for each logical operation without persistence:

```python
class BatchSubmitter:
    def __init__(self, client):
        self.client = client

    def submit(self, jobs, metadata=None):
        """Submit batch with automatic retry."""
        import uuid

        idempotency_key = str(uuid.uuid4())
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                return self.client.batch.create(
                    jobs=jobs,
                    metadata=metadata,
                    extra_headers={"Idempotency-Key": idempotency_key}
                )
            except (spatialise.APIConnectionError, spatialise.InternalServerError):
                if attempt == max_attempts - 1:
                    raise
                time.sleep(2 ** attempt)
```

### Pattern 2: Database-Backed Idempotency

Store idempotency keys in a database for correlation across application restarts:

```python
from sqlalchemy import Column, String, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class BatchRequest(Base):
    __tablename__ = 'batch_requests'

    idempotency_key = Column(String(255), primary_key=True)
    batch_id = Column(String(255))
    request_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class PersistentBatchSubmitter:
    def __init__(self, client, db_url):
        self.client = client
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)

    def submit(self, jobs, metadata=None):
        """Submit batch with database-backed idempotency."""
        import uuid

        session = self.Session()
        try:
            # Generate new key
            idempotency_key = str(uuid.uuid4())

            # Make API request
            batch = self.client.batch.create(
                jobs=jobs,
                metadata=metadata,
                extra_headers={"Idempotency-Key": idempotency_key}
            )

            # Store for future reference
            request = BatchRequest(
                idempotency_key=idempotency_key,
                batch_id=batch.batch_id,
                request_payload={"jobs": jobs, "metadata": metadata}
            )
            session.add(request)
            session.commit()

            return batch
        finally:
            session.close()

    def retry_by_key(self, idempotency_key):
        """Retry request using stored idempotency key."""
        session = self.Session()
        try:
            request = session.query(BatchRequest).filter_by(
                idempotency_key=idempotency_key
            ).first()

            if not request:
                raise ValueError(f"No request found for key: {idempotency_key}")

            # Retry with original key and payload
            payload = request.request_payload
            return self.client.batch.create(
                jobs=payload['jobs'],
                metadata=payload.get('metadata'),
                extra_headers={"Idempotency-Key": idempotency_key}
            )
        finally:
            session.close()
```

### Pattern 3: Cache-Based Deduplication

Use Redis or similar cache to prevent duplicate requests:

```python
import redis
import json
import hashlib

class CachedBatchSubmitter:
    def __init__(self, client, redis_url):
        self.client = client
        self.redis = redis.from_url(redis_url)
        self.cache_ttl = 86400  # 24 hours, matching API TTL

    def submit(self, jobs, metadata=None):
        """Submit batch with cache-based deduplication."""
        # Create content hash for deduplication
        content = json.dumps(
            {"jobs": jobs, "metadata": metadata},
            sort_keys=True
        )
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        cache_key = f"batch:request:{content_hash}"

        # Check cache
        cached_batch_id = self.redis.get(cache_key)
        if cached_batch_id:
            # Return existing batch status
            return self.client.batch.retrieve_status(
                cached_batch_id.decode('utf-8')
            )

        # Create new batch
        idempotency_key = f"hash-{content_hash[:32]}"
        batch = self.client.batch.create(
            jobs=jobs,
            metadata=metadata,
            extra_headers={"Idempotency-Key": idempotency_key}
        )

        # Cache batch ID
        self.redis.setex(cache_key, self.cache_ttl, batch.batch_id)

        return batch
```

## Best Practices

### Always Use Idempotency Keys in Production

Production systems should always include idempotency keys:

```python
# Production code
def submit_production_batch(client, jobs, metadata=None):
    import uuid
    return client.batch.create(
        jobs=jobs,
        metadata=metadata,
        extra_headers={"Idempotency-Key": str(uuid.uuid4())}
    )

# Acceptable for testing only
def submit_test_batch(client, jobs, metadata=None):
    return client.batch.create(jobs=jobs, metadata=metadata)
```

### Store Keys for Debugging

Log idempotency keys for troubleshooting:

```python
import logging

logger = logging.getLogger(__name__)

def submit_with_logging(client, jobs, metadata=None):
    import uuid

    idempotency_key = str(uuid.uuid4())

    logger.info(
        "Submitting batch",
        extra={
            "idempotency_key": idempotency_key,
            "job_count": len(jobs)
        }
    )

    try:
        batch = client.batch.create(
            jobs=jobs,
            metadata=metadata,
            extra_headers={"Idempotency-Key": idempotency_key}
        )

        logger.info(
            "Batch created",
            extra={
                "idempotency_key": idempotency_key,
                "batch_id": batch.batch_id
            }
        )

        return batch
    except Exception as e:
        logger.error(
            "Batch creation failed",
            extra={
                "idempotency_key": idempotency_key,
                "error": str(e)
            },
            exc_info=True
        )
        raise
```

### Avoid Key Reuse Across Operations

Each distinct operation requires a unique key:

```python
# Incorrect: Reusing key for different operations
shared_key = "my-project-batch"
batch1 = client.batch.create(
    jobs=jobs_a,
    extra_headers={"Idempotency-Key": shared_key}
)
batch2 = client.batch.create(
    jobs=jobs_b,  # Different jobs
    extra_headers={"Idempotency-Key": shared_key}  # Same key - ERROR
)

# Correct: Unique key per operation
import uuid
batch1 = client.batch.create(
    jobs=jobs_a,
    extra_headers={"Idempotency-Key": str(uuid.uuid4())}
)
batch2 = client.batch.create(
    jobs=jobs_b,
    extra_headers={"Idempotency-Key": str(uuid.uuid4())}
)
```

### Use Descriptive Key Formats

For debugging, include context in keys:

```python
from datetime import datetime
import uuid

def generate_descriptive_key(project_name, operation_type):
    """Generate human-readable idempotency key."""
    timestamp = datetime.utcnow().isoformat()
    unique_id = uuid.uuid4().hex[:8]
    return f"{project_name}-{operation_type}-{timestamp}-{unique_id}"

# Usage
key = generate_descriptive_key("soil-analysis", "batch")
# Example: "soil-analysis-batch-2025-01-15T10:30:00-a3f5d9e2"
```

## Integration with Client Retries

The SDK's built-in retry mechanism works with idempotency:

```python
# Configure retries at client level
client = SpatialiseSoilPrediction(max_retries=3)

# Automatic retries use same idempotency key
batch = client.batch.create(
    jobs=[...],
    extra_headers={"Idempotency-Key": str(uuid.uuid4())}
)
```

The SDK automatically retries:
- Network errors (`APIConnectionError`)
- 408 Request Timeout
- 409 Conflict
- 429 Rate Limit
- 500+ Internal Server Errors

Manual retry implementation provides finer control:

```python
def create_batch_with_custom_retry(client, jobs, metadata=None):
    """Custom retry with exponential backoff and jitter."""
    import uuid
    import random

    idempotency_key = str(uuid.uuid4())
    max_retries = 5
    base_delay = 1

    for attempt in range(max_retries):
        try:
            return client.batch.create(
                jobs=jobs,
                metadata=metadata,
                extra_headers={"Idempotency-Key": idempotency_key}
            )
        except (spatialise.APIConnectionError,
                spatialise.InternalServerError) as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt), 60)
            jitter = random.uniform(0, delay * 0.1)
            time.sleep(delay + jitter)
```

## See Also

- [Webhook Integration](./webhooks.md) - Idempotency in webhook handlers
- [Rate Limiting](./rate-limiting.md) - Combining idempotency with rate limit handling
- [Production Patterns](./production-patterns.md) - Database-backed idempotency patterns

# Webhook Integration Guide

This guide provides comprehensive documentation for integrating webhooks with the Spatialise Soil Prediction API, including security best practices, HMAC signature verification, and production deployment patterns.

## Table of Contents

- [Overview](#overview)
- [Architecture: Webhooks vs Polling](#architecture-webhooks-vs-polling)
- [HMAC Signature Verification](#hmac-signature-verification)
- [Webhook Payload Structure](#webhook-payload-structure)
- [Security Best Practices](#security-best-practices)
- [Local Development & Testing](#local-development--testing)
- [Production Deployment](#production-deployment)
- [Error Handling](#error-handling)
- [Complete Implementation Example](#complete-implementation-example)

## Overview

Webhooks provide a push-based notification system that eliminates the need for polling. When your batch completes processing, Spatialise sends an HTTP POST request to your configured endpoint with the results.

**Benefits over polling:**
- Real-time notifications (no polling delay)
- Reduced API calls and costs
- Lower server resource usage
- Event-driven architecture

## Architecture: Webhooks vs Polling

### Polling Pattern

```
Your App                  Spatialise API
   |                            |
   |  1. Create batch           |
   |--------------------------->|
   |  2. Batch ID               |
   |<---------------------------|
   |                            |
   |  3. Get status (pending)   |
   |--------------------------->|
   |<---------------------------|
   |                            |
   | ... wait 10 seconds ...    |
   |                            |
   |  4. Get status (pending)   |
   |--------------------------->|
   |<---------------------------|
   |                            |
   | ... wait 10 seconds ...    |
   |                            |
   |  5. Get status (completed) |
   |--------------------------->|
   |<---------------------------|
```

**Downsides:** Wastes API quota, introduces delay, ties up resources

### Webhook Pattern

```
Your App                  Spatialise API
   |                            |
   |  1. Create batch           |
   |    (with webhook_url)      |
   |--------------------------->|
   |  2. Batch ID               |
   |<---------------------------|
   |                            |
   | Your app is free to        |
   | do other work...           |
   |                            |
   |                       (Processing...)
   |                            |
   |  3. POST completion data   |
   |<---------------------------|
   |  4. Return 200 OK          |
   |--------------------------->|
```

**Advantages:** Instant notification, no polling overhead, event-driven

## HMAC Signature Verification

### What is HMAC?

HMAC (Hash-based Message Authentication Code) is a cryptographic technique that ensures:
1. **Authentication:** The webhook came from Spatialise (not an attacker)
2. **Integrity:** The payload hasn't been tampered with
3. **Non-repudiation:** Spatialise can't deny sending it

### How HMAC-SHA256 Works

```
┌─────────────────┐
│  Webhook Secret │  (Shared between you and Spatialise)
└────────┬────────┘
         │
         ├──────────┐
         │          │
         v          v
    ┌────────┐  ┌──────────┐
    │  HMAC  │  │ Raw JSON │
    │  Func  │<─│ Payload  │
    └────┬───┘  └──────────┘
         │
         v
    ┌─────────────────────────────────────┐
    │ X-Spatialise-Signature: abc123...   │  (hex digest)
    └─────────────────────────────────────┘
```

### Step-by-Step Verification

**1. Extract signature from header**
```python
signature = request.headers.get("X-Spatialise-Signature")
```

**2. Get raw request body**
```python
# CRITICAL: Use raw bytes, not parsed JSON
raw_body = await request.body()  # FastAPI
# or
raw_body = request.get_data()    # Flask
```

**3. Compute expected signature**
```python
import hmac
import hashlib

expected_signature = hmac.new(
    key=WEBHOOK_SECRET.encode('utf-8'),  # Your secret as bytes
    msg=raw_body,                         # Raw request body
    digestmod=hashlib.sha256              # SHA-256 hash function
).hexdigest()                             # Convert to hex string
```

**4. Compare signatures using constant-time comparison**
```python
if not hmac.compare_digest(signature, expected_signature):
    raise Exception("Invalid signature - webhook rejected")
```

### Why Constant-Time Comparison?

```python
# VULNERABLE to timing attacks - DO NOT USE
if signature == expected_signature:
    pass

# SECURE constant-time comparison - USE THIS
if hmac.compare_digest(signature, expected_signature):
    pass
```

**Timing attack explanation:**

Normal string comparison (`==`) stops at the first mismatched character. An attacker can measure response time to guess the signature byte-by-byte:

```
Attacker tries: "a000..." → Fast rejection (1st char wrong)
Attacker tries: "b000..." → Slower rejection (1st char matches!)
... eventually discovers: "badf00d..." → Valid signature
```

`hmac.compare_digest()` always takes the same time regardless of where differences occur, preventing this attack.

## Webhook Payload Structure

### Complete Payload Schema

```json
{
  "batch_id": "batch_abc123xyz",
  "status": "completed",
  "completed_jobs": 8,
  "failed_jobs": 2,
  "total_jobs": 10,
  "created_at": "2025-01-15T10:30:00Z",
  "completed_at": "2025-01-15T10:45:00Z",
  "metadata": {
    "project": "Drenthe Analysis",
    "custom_field": "any value"
  },
  "jobs": [
    {
      "job_id": "job_001",
      "status": "completed",
      "signed_cog_url": "https://storage.googleapis.com/spatialise-results/batch_abc/job_001.tif?signature=...",
      "signed_url_expires_at": "2025-01-16T10:45:00Z",
      "error_message": null,
      "created_at": "2025-01-15T10:30:00Z",
      "completed_at": "2025-01-15T10:42:00Z"
    },
    {
      "job_id": "job_002",
      "status": "failed",
      "signed_cog_url": null,
      "signed_url_expires_at": null,
      "error_message": "Invalid polygon: self-intersecting coordinates",
      "created_at": "2025-01-15T10:30:00Z",
      "completed_at": "2025-01-15T10:35:00Z"
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `batch_id` | string | Unique batch identifier |
| `status` | string | Batch status: `completed`, `failed`, or `partial` |
| `completed_jobs` | integer | Number of successfully completed jobs |
| `failed_jobs` | integer | Number of failed jobs |
| `total_jobs` | integer | Total jobs in batch |
| `created_at` | ISO 8601 | When batch was created |
| `completed_at` | ISO 8601 | When batch finished processing |
| `metadata` | object | Your custom metadata from batch creation |
| `jobs` | array | Array of job results |
| `jobs[].job_id` | string | Unique job identifier |
| `jobs[].status` | string | Job status: `completed` or `failed` |
| `jobs[].signed_cog_url` | string? | Signed URL to download GeoTIFF (24hr expiry) |
| `jobs[].signed_url_expires_at` | ISO 8601? | When the signed URL expires |
| `jobs[].error_message` | string? | Error description if job failed |

### Type-Safe Parsing (Python)

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Job(BaseModel):
    job_id: str
    status: str
    signed_cog_url: Optional[str] = None
    signed_url_expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: datetime

class WebhookPayload(BaseModel):
    batch_id: str
    status: str
    completed_jobs: int
    failed_jobs: int
    total_jobs: int
    created_at: datetime
    completed_at: datetime
    metadata: Optional[dict] = None
    jobs: List[Job]

# In your webhook handler
payload = WebhookPayload.model_validate_json(raw_body)
```

## Security Best Practices

### 1. Secret Management

**Never hardcode secrets:**
```python
# DON'T DO THIS
WEBHOOK_SECRET = "my-secret-123"
```

**Use environment variables:**
```python
import os
WEBHOOK_SECRET = os.environ["SPATIALISE_WEBHOOK_SECRET"]
```

**Use secret management services (production):**
```python
# AWS Secrets Manager
import boto3
secrets_client = boto3.client('secretsmanager')
response = secrets_client.get_secret_value(SecretId='spatialise/webhook-secret')
WEBHOOK_SECRET = response['SecretString']

# GCP Secret Manager
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
response = client.access_secret_version(name="projects/123/secrets/webhook-secret/versions/latest")
WEBHOOK_SECRET = response.payload.data.decode('UTF-8')
```

### 2. Enforce HTTPS

**Always use HTTPS webhook URLs in production:**
```python
batch = client.batch.create(
    jobs=[...],
    webhook_url="https://api.example.com/webhooks/spatialise",  # HTTPS - secure
    # NOT: http://api.example.com/webhooks/spatialise  # HTTP - insecure!
    webhook_secret=WEBHOOK_SECRET
)
```

HTTP webhooks expose your secret in transit, allowing man-in-the-middle attacks.

### 3. Validate All Input

```python
@app.post("/webhooks/spatialise")
async def handle_webhook(request: Request):
    # 1. Verify signature FIRST
    if not verify_signature(request):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Parse and validate payload structure
    try:
        payload = WebhookPayload.model_validate_json(await request.body())
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    # 3. Validate business logic
    if payload.total_jobs != payload.completed_jobs + payload.failed_jobs:
        # Inconsistent data - log and alert
        logger.error(f"Inconsistent job counts in batch {payload.batch_id}")

    # 4. Process webhook
    process_batch_completion(payload)

    return {"status": "received"}
```

### 4. Implement Idempotency

Spatialise may retry failed webhooks. Your handler must be idempotent:

```python
async def handle_webhook(payload: WebhookPayload):
    # Check if we've already processed this webhook
    if await database.webhook_processed(payload.batch_id):
        logger.info(f"Webhook for {payload.batch_id} already processed, skipping")
        return {"status": "already_processed"}

    # Process the webhook
    await process_batch_completion(payload)

    # Mark as processed
    await database.mark_webhook_processed(payload.batch_id)

    return {"status": "received"}
```

### 5. Implement Replay Attack Protection

Add timestamp validation to reject old webhook deliveries:

```python
from datetime import datetime, timedelta

def verify_webhook_freshness(payload: WebhookPayload, max_age_minutes=5):
    """Reject webhooks older than max_age_minutes."""
    webhook_age = datetime.utcnow() - payload.completed_at

    if webhook_age > timedelta(minutes=max_age_minutes):
        raise HTTPException(
            status_code=401,
            detail=f"Webhook too old: {webhook_age.total_seconds()}s"
        )
```

## Local Development & Testing

### Using ngrok for Local Testing

1. **Install ngrok:**
```bash
brew install ngrok  # macOS
# or download from https://ngrok.com/download
```

2. **Start your local webhook server:**
```bash
# Terminal 1
python examples/webhook_handler_fastapi.py
# Server running on http://localhost:8000
```

3. **Create ngrok tunnel:**
```bash
# Terminal 2
ngrok http 8000
```

You'll see output like:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

4. **Use the ngrok URL for webhooks:**
```python
client.batch.create(
    jobs=[...],
    webhook_url="https://abc123.ngrok.io/webhooks/spatialise/batch-complete",
    webhook_secret="test-secret-123"
)
```

### Testing Signature Verification

Create a test script to verify your HMAC implementation:

```python
import hmac
import hashlib
import json

# Your webhook secret
WEBHOOK_SECRET = "test-secret-123"

# Simulate a webhook payload
payload = {
    "batch_id": "batch_test",
    "status": "completed",
    "completed_jobs": 1,
    "failed_jobs": 0,
    "total_jobs": 1,
    "jobs": []
}

# Convert to JSON bytes (what Spatialise sends)
payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

# Compute signature (what Spatialise does)
signature = hmac.new(
    WEBHOOK_SECRET.encode('utf-8'),
    payload_bytes,
    hashlib.sha256
).hexdigest()

print(f"Payload: {payload_bytes}")
print(f"Signature: {signature}")

# Test verification
expected = hmac.new(
    WEBHOOK_SECRET.encode('utf-8'),
    payload_bytes,
    hashlib.sha256
).hexdigest()

assert hmac.compare_digest(signature, expected), "Signature mismatch!"
print("SUCCESS: Signature verification works!")
```

### Debugging Tips

**1. Log raw request details:**
```python
@app.post("/webhooks/spatialise")
async def handle_webhook(request: Request):
    # Log everything for debugging
    logger.debug(f"Headers: {dict(request.headers)}")
    raw_body = await request.body()
    logger.debug(f"Raw body: {raw_body}")
    logger.debug(f"Signature: {request.headers.get('X-Spatialise-Signature')}")

    # ... verification logic
```

**2. Test with curl:**
```bash
# Compute signature
SECRET="test-secret-123"
PAYLOAD='{"batch_id":"test","status":"completed","jobs":[]}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send test webhook
curl -X POST http://localhost:8000/webhooks/spatialise \
  -H "Content-Type: application/json" \
  -H "X-Spatialise-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

**3. Common issues:**

| Issue | Cause | Solution |
|-------|-------|----------|
| Signature mismatch | Using parsed JSON instead of raw bytes | Use `request.body()` not `request.json()` |
| Signature mismatch | Secret encoding issue | Ensure `.encode('utf-8')` on secret |
| 401 errors | Wrong secret | Verify secret matches batch creation |
| Connection refused | Firewall/ngrok not running | Check ngrok status, firewall rules |

## Production Deployment

### Cloud Platform Options

#### AWS Lambda + API Gateway

```python
# lambda_function.py
import json
import hmac
import hashlib
import os

WEBHOOK_SECRET = os.environ['SPATIALISE_WEBHOOK_SECRET']

def lambda_handler(event, context):
    # Extract body and headers
    body = event['body']
    signature = event['headers'].get('x-spatialise-signature')

    # Verify signature
    expected = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Invalid signature'})
        }

    # Process webhook
    payload = json.loads(body)
    process_batch_completion(payload)

    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'received'})
    }
```

**Deployment:**
```bash
# Package dependencies
pip install -r requirements.txt -t .
zip -r function.zip .

# Deploy
aws lambda create-function \
  --function-name spatialise-webhook-handler \
  --runtime python3.11 \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --environment Variables={SPATIALISE_WEBHOOK_SECRET=your-secret}
```

#### Google Cloud Run

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD exec uvicorn webhook_handler_fastapi:app --host 0.0.0.0 --port $PORT
```

```bash
# Deploy
gcloud run deploy spatialise-webhook \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars SPATIALISE_WEBHOOK_SECRET=projects/123/secrets/webhook-secret
```

#### Heroku

```bash
# Procfile
web: uvicorn webhook_handler_fastapi:app --host 0.0.0.0 --port $PORT

# Deploy
heroku create spatialise-webhook
heroku config:set SPATIALISE_WEBHOOK_SECRET=your-secret
git push heroku main
```

### Scaling Considerations

**1. Async processing for long-running tasks:**
```python
from fastapi import BackgroundTasks

@app.post("/webhooks/spatialise")
async def handle_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks
):
    # Quick signature verification and acknowledgment
    verify_signature(...)

    # Process in background (don't block webhook response)
    background_tasks.add_task(process_batch_completion, payload)

    # Return immediately
    return {"status": "received"}

async def process_batch_completion(payload: WebhookPayload):
    # Long-running tasks:
    # - Download GeoTIFFs
    # - Process images
    # - Update database
    # - Send notifications
    pass
```

**2. Queue-based architecture:**
```python
import redis
from rq import Queue

redis_conn = redis.from_url(os.environ['REDIS_URL'])
queue = Queue('webhook-processing', connection=redis_conn)

@app.post("/webhooks/spatialise")
async def handle_webhook(payload: WebhookPayload):
    verify_signature(...)

    # Add to queue for worker processing
    queue.enqueue(process_batch_completion, payload.model_dump())

    return {"status": "queued"}
```

### Monitoring & Alerting

**1. Structured logging:**
```python
import structlog

logger = structlog.get_logger()

@app.post("/webhooks/spatialise")
async def handle_webhook(payload: WebhookPayload):
    logger.info(
        "webhook_received",
        batch_id=payload.batch_id,
        status=payload.status,
        completed_jobs=payload.completed_jobs,
        failed_jobs=payload.failed_jobs
    )

    # Process...

    logger.info(
        "webhook_processed",
        batch_id=payload.batch_id,
        processing_time_ms=elapsed
    )
```

**2. Health checks:**
```python
@app.get("/health")
async def health_check():
    # Verify dependencies
    db_healthy = await check_database()
    redis_healthy = await check_redis()

    if not (db_healthy and redis_healthy):
        raise HTTPException(status_code=503, detail="Unhealthy")

    return {"status": "healthy"}
```

**3. Error alerting:**
```python
import sentry_sdk

sentry_sdk.init(dsn=os.environ['SENTRY_DSN'])

@app.post("/webhooks/spatialise")
async def handle_webhook(payload: WebhookPayload):
    try:
        verify_signature(...)
        process_batch_completion(payload)
    except Exception as e:
        # Automatically sent to Sentry
        sentry_sdk.capture_exception(e)
        raise
```

## Error Handling

### Webhook Retry Behavior

Spatialise implements automatic retries for failed webhook deliveries:

- **Retry schedule:** Exponential backoff (10s, 30s, 1m, 5m, 15m)
- **Max retries:** 5 attempts
- **Retry conditions:** HTTP 5xx errors, timeouts, connection failures
- **No retry:** HTTP 4xx errors (considered permanent failures)

**Your webhook handler should:**
1. Return `200 OK` for successful processing
2. Return `4xx` for invalid payloads (won't retry)
3. Return `5xx` for temporary failures (will retry)

### Idempotency Implementation

```python
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class ProcessedWebhook(Base):
    __tablename__ = 'processed_webhooks'

    batch_id = Column(String, primary_key=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    webhook_data = Column(JSON)

engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)

@app.post("/webhooks/spatialise")
async def handle_webhook(payload: WebhookPayload):
    verify_signature(...)

    session = Session()
    try:
        # Check if already processed
        existing = session.query(ProcessedWebhook).filter_by(
            batch_id=payload.batch_id
        ).first()

        if existing:
            logger.info(f"Webhook {payload.batch_id} already processed")
            return {"status": "already_processed"}

        # Process the webhook
        result = process_batch_completion(payload)

        # Record as processed
        session.add(ProcessedWebhook(
            batch_id=payload.batch_id,
            webhook_data=payload.model_dump()
        ))
        session.commit()

        return {"status": "received", "result": result}

    except Exception as e:
        session.rollback()
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
```

### Handling Failed Webhooks

If all retries fail, you can fall back to polling:

```python
async def process_batch_with_fallback(batch_id: str):
    """Process batch with webhook + polling fallback."""

    # Wait for webhook notification
    webhook_received = await wait_for_webhook(batch_id, timeout=3600)

    if webhook_received:
        logger.info(f"Batch {batch_id} processed via webhook")
        return

    # Fallback to polling
    logger.warning(f"Webhook timeout for {batch_id}, falling back to polling")
    status = await poll_batch_status(batch_id)
    process_batch_completion(status)
```

## Complete Implementation Example

Here's a production-ready webhook handler with all best practices:

```python
#!/usr/bin/env python3
"""
Production-ready webhook handler with security, idempotency, and monitoring.
"""

import os
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, ValidationError
from sqlalchemy import Column, String, DateTime, JSON, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import sentry_sdk

# Initialize monitoring
sentry_sdk.init(dsn=os.environ.get('SENTRY_DSN'))
logger = structlog.get_logger()

# Database setup
Base = declarative_base()
engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)

class ProcessedWebhook(Base):
    __tablename__ = 'processed_webhooks'
    batch_id = Column(String, primary_key=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    payload = Column(JSON)

Base.metadata.create_all(engine)

# Pydantic models
class Job(BaseModel):
    job_id: str
    status: str
    signed_cog_url: Optional[str] = None
    error_message: Optional[str] = None

class WebhookPayload(BaseModel):
    batch_id: str
    status: str
    completed_jobs: int
    failed_jobs: int
    total_jobs: int
    jobs: list[Job]
    metadata: Optional[dict] = None
    completed_at: datetime

# FastAPI app
app = FastAPI(title="Spatialise Webhook Handler")

WEBHOOK_SECRET = os.environ['SPATIALISE_WEBHOOK_SECRET']
MAX_WEBHOOK_AGE_MINUTES = 5

def verify_signature(request: Request, body: bytes) -> bool:
    """Verify HMAC signature from X-Spatialise-Signature header."""
    signature = request.headers.get("x-spatialise-signature")
    if not signature:
        return False

    expected = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)

def verify_freshness(payload: WebhookPayload) -> None:
    """Reject webhooks older than MAX_WEBHOOK_AGE_MINUTES."""
    age = datetime.utcnow() - payload.completed_at
    if age > timedelta(minutes=MAX_WEBHOOK_AGE_MINUTES):
        raise HTTPException(
            status_code=401,
            detail=f"Webhook too old: {age.total_seconds()}s"
        )

async def process_batch_completion(payload: WebhookPayload):
    """Process completed batch (runs in background)."""
    logger.info(
        "processing_batch",
        batch_id=payload.batch_id,
        completed=payload.completed_jobs,
        failed=payload.failed_jobs
    )

    for job in payload.jobs:
        if job.status == "completed":
            # Download and process GeoTIFF
            logger.info("downloading_result", job_id=job.job_id, url=job.signed_cog_url)
            # await download_and_process_geotiff(job.signed_cog_url)

        elif job.status == "failed":
            # Log error and alert
            logger.error("job_failed", job_id=job.job_id, error=job.error_message)
            # await send_failure_alert(job)

    logger.info("batch_processing_complete", batch_id=payload.batch_id)

@app.post("/webhooks/spatialise/batch-complete")
async def handle_batch_complete(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle batch completion webhook from Spatialise."""

    # Get raw body for signature verification
    body = await request.body()

    # 1. Verify HMAC signature
    if not verify_signature(request, body):
        logger.warning("invalid_signature", headers=dict(request.headers))
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Parse and validate payload
    try:
        payload = WebhookPayload.model_validate_json(body)
    except ValidationError as e:
        logger.error("invalid_payload", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    # 3. Verify webhook freshness (replay attack protection)
    verify_freshness(payload)

    # 4. Check idempotency
    session = Session()
    try:
        existing = session.query(ProcessedWebhook).filter_by(
            batch_id=payload.batch_id
        ).first()

        if existing:
            logger.info("webhook_already_processed", batch_id=payload.batch_id)
            return {"status": "already_processed"}

        # 5. Record as processed (before processing for idempotency)
        session.add(ProcessedWebhook(
            batch_id=payload.batch_id,
            payload=payload.model_dump()
        ))
        session.commit()

    except Exception as e:
        session.rollback()
        logger.error("database_error", error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        session.close()

    # 6. Process in background (don't block webhook response)
    background_tasks.add_task(process_batch_completion, payload)

    logger.info("webhook_accepted", batch_id=payload.batch_id)
    return {"status": "received", "batch_id": payload.batch_id}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
```

### Environment Variables

```bash
# Required
export SPATIALISE_WEBHOOK_SECRET="your-webhook-secret-here"
export DATABASE_URL="postgresql://user:pass@localhost/db"

# Optional
export SENTRY_DSN="https://xxx@sentry.io/xxx"
export PORT="8000"
```

### Testing the Implementation

```bash
# 1. Set up environment
export SPATIALISE_WEBHOOK_SECRET="test-secret"
export DATABASE_URL="sqlite:///./test.db"

# 2. Run the server
python webhook_handler.py

# 3. Test with curl
./test_webhook.sh
```

---

## Additional Resources

- [HMAC Wikipedia](https://en.wikipedia.org/wiki/HMAC) - Technical details
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Web framework
- [ngrok Documentation](https://ngrok.com/docs) - Local testing
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## Next Steps

- [Idempotency Guide](./idempotency.md) - Detailed idempotency patterns
- [Rate Limiting Guide](./rate-limiting.md) - Handling API limits
- [Production Patterns](./production-patterns.md) - Database integration, queues
- [GeoTIFF Processing](./geotiff-processing.md) - Working with result files

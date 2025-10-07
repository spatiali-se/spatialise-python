#!/usr/bin/env python3
"""
FastAPI webhook handler example.

This is an example web server that receives webhook notifications
from Spatialise when batch predictions complete.

To use:
1. Install dependencies: pip install fastapi uvicorn
2. Set SPATIALISE_WEBHOOK_SECRET environment variable
3. Run: uvicorn webhook_handler_fastapi:app --host 0.0.0.0 --port 8000
4. Expose to internet (e.g., using ngrok for testing)
5. Use the public URL when creating batches with webhooks

For production, deploy this to a proper web server (e.g., Heroku, AWS, GCP).
"""

import os
import hmac
import hashlib
from typing import Any, Dict, List, Optional

from fastapi import Header, FastAPI, Request, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Spatialise Webhook Handler")

# Same secret used when creating the batch
WEBHOOK_SECRET = os.environ.get("SPATIALISE_WEBHOOK_SECRET", "your-secret-key")


# Pydantic models for type safety
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
    jobs: List[Job]
    metadata: Optional[Dict[str, Any]] = None


@app.post("/webhooks/spatialise/batch-complete")
async def handle_batch_complete(
    payload: WebhookPayload,
    request: Request,
    x_spatialise_signature: str = Header(None, alias="X-Spatialise-Signature"),
):
    """Handle batch completion webhook from Spatialise."""

    # Verify webhook signature
    if not x_spatialise_signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    # Get raw body for signature verification
    body = await request.body()

    # Compute expected signature
    expected_signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

    # Verify signature using constant-time comparison
    if not hmac.compare_digest(x_spatialise_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Process the webhook
    print(f"Batch {payload.batch_id} completed!")
    print(f"  Status: {payload.status}")
    print(f"  Completed: {payload.completed_jobs}/{payload.total_jobs}")
    print(f"  Failed: {payload.failed_jobs}")

    # Process each job
    for job in payload.jobs:
        if job.status == "completed":
            print(f"  ✓ Job {job.job_id}: {job.signed_cog_url}")

            # Here you could:
            # - Download the GeoTIFF
            # - Store the URL in a database
            # - Send a notification email
            # - Trigger downstream processing

        elif job.status == "failed":
            print(f"  ✗ Job {job.job_id}: {job.error_message}")

            # Here you could:
            # - Log the error
            # - Send an alert
            # - Retry the job

    # Acknowledge receipt
    return {"status": "received", "batch_id": payload.batch_id}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with documentation."""
    return {
        "service": "Spatialise Webhook Handler",
        "endpoints": {
            "webhook": "/webhooks/spatialise/batch-complete",
            "health": "/health",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Spatialise Webhook Handler (FastAPI)")
    print("=" * 60)
    print()
    print("Run with:")
    print("  uvicorn webhook_handler_fastapi:app --host 0.0.0.0 --port 8000")
    print()
    print("Endpoints:")
    print("  Webhook: http://0.0.0.0:8000/webhooks/spatialise/batch-complete")
    print("  Health: http://0.0.0.0:8000/health")
    print("  Docs: http://0.0.0.0:8000/docs")
    print()
    print("To expose this locally for testing, use ngrok:")
    print("  ngrok http 8000")
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)

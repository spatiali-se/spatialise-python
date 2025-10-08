#!/usr/bin/env python3
"""
Flask webhook handler example.

This is an example web server that receives webhook notifications
from Spatialise when batch predictions complete.

To use:
1. Install Flask: pip install flask
2. Set SPATIALISE_WEBHOOK_SECRET environment variable
3. Run: python webhook_handler_flask.py
4. Expose to internet (e.g., using ngrok for testing)
5. Use the public URL when creating batches with webhooks

For production, deploy this to a proper web server (e.g., Heroku, AWS, GCP).
"""

import os
import hmac
import hashlib

from flask import Flask, jsonify, request

app = Flask(__name__)

# Same secret used when creating the batch
WEBHOOK_SECRET = os.environ.get("SPATIALISE_WEBHOOK_SECRET", "your-secret-key")


@app.route("/webhooks/spatialise/batch-complete", methods=["POST"])
def handle_batch_complete():
    """Handle batch completion webhook from Spatialise."""

    # Verify webhook signature
    signature = request.headers.get("X-Spatialise-Signature")
    if not signature:
        app.logger.warning("Webhook received without signature")
        return jsonify({"error": "Missing signature"}), 401

    payload = request.get_data()

    # Compute expected signature
    expected_signature = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    # Verify signature using constant-time comparison
    if not hmac.compare_digest(signature, expected_signature):
        app.logger.warning("Webhook signature verification failed")
        return jsonify({"error": "Invalid signature"}), 401

    # Process the webhook payload
    data = request.get_json()
    batch_id = data.get("batch_id")
    status = data.get("status")
    completed_jobs = data.get("completed_jobs", 0)
    failed_jobs = data.get("failed_jobs", 0)

    app.logger.info(f"Batch {batch_id} completed!")
    app.logger.info(f"  Status: {status}")
    app.logger.info(f"  Completed: {completed_jobs}")
    app.logger.info(f"  Failed: {failed_jobs}")

    # Process completed jobs
    for job in data.get("jobs", []):
        job_id = job.get("job_id")
        job_status = job.get("status")

        if job_status == "completed":
            cog_url = job.get("signed_cog_url")
            app.logger.info(f"  Job {job_id}: {cog_url}")

            # Here you could:
            # - Download the GeoTIFF
            # - Store the URL in a database
            # - Send a notification email
            # - Trigger downstream processing

        elif job_status == "failed":
            error = job.get("error_message")
            app.logger.error(f"  FAILED Job {job_id}: {error}")

            # Here you could:
            # - Log the error
            # - Send an alert
            # - Retry the job

    # Acknowledge receipt
    return jsonify({"status": "received", "batch_id": batch_id}), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    print("=" * 60)
    print("Spatialise Webhook Handler (Flask)")
    print("=" * 60)
    print()
    print(f"Webhook endpoint: http://0.0.0.0:8000/webhooks/spatialise/batch-complete")
    print(f"Health check: http://0.0.0.0:8000/health")
    print()
    print("To expose this locally for testing, use ngrok:")
    print("  ngrok http 8000")
    print()
    print("=" * 60)

    # Run the Flask app
    app.run(host="0.0.0.0", port=8000, debug=True)

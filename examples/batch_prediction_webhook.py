#!/usr/bin/env python3
"""
Webhook example: Create batch predictions with webhook notifications.

This example demonstrates:
1. Using webhooks to get notified when batch processing completes
2. Setting up webhook authentication with secrets
3. Handling webhook callbacks (requires separate web server)

Note: This example shows how to CREATE a batch with webhook configuration.
To handle webhook callbacks, you'll need a separate web server (e.g., Flask, FastAPI).
"""

import os

from spatialise import SpatialiseSoilPrediction

# Initialize the client
client = SpatialiseSoilPrediction(
    api_key=os.environ.get("SPATIALISE_API_KEY"),
)

# Your webhook endpoint URL (must be publicly accessible)
# This is where Spatialise will send notifications when the batch completes
WEBHOOK_URL = "https://your-domain.com/webhooks/spatialise/batch-complete"

# Secret for webhook authentication (keep this secure!)
# The webhook payload will include a signature that you can verify using this secret
WEBHOOK_SECRET = os.environ.get("SPATIALISE_WEBHOOK_SECRET", "your-secret-key")


def create_batch_with_webhook():
    """Create a batch with webhook notification."""

    jobs = [
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
        },
        {
            "year": 2022,
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
        },
    ]

    print("Creating batch with webhook notification...")
    batch = client.batch.create(
        jobs=jobs,
        webhook_url=WEBHOOK_URL,
        webhook_secret=WEBHOOK_SECRET,
        metadata={
            "project": "Webhook Example",
            "notification_email": "analyst@example.com",
        },
    )

    print(f"Batch created: {batch.batch_id}")
    print(f"  Status: {batch.status}")
    print(f"  Total jobs: {batch.total_jobs}")
    print(f"  Webhook URL: {WEBHOOK_URL}")
    print()
    print("When the batch completes, Spatialise will POST to your webhook URL with the batch results.")

    return batch


def main():
    print("=" * 60)
    print("Batch Prediction with Webhook Notification")
    print("=" * 60)
    print()

    # Create the batch
    batch = create_batch_with_webhook()

    print()
    print("Next steps:")
    print("1. Set up a webhook handler at the configured URL")
    print("2. Wait for the webhook notification (no polling needed!)")
    print("3. Process the results when notified")
    print()
    print("See webhook_handler_flask.py or webhook_handler_fastapi.py")
    print("for example webhook server implementations.")


if __name__ == "__main__":
    main()

# Production Patterns

This guide covers production-ready patterns for deploying the Spatialise SDK, including secret management, database integration, asynchronous processing, logging, monitoring, and error recovery strategies.

## Secret Management

### Environment Variables

Store sensitive credentials in environment variables:

```python
import os
from spatialise import SpatialiseSoilPrediction

# Load from environment
api_key = os.environ['SPATIALISE_API_KEY']
client = SpatialiseSoilPrediction(api_key=api_key)
```

Use `.env` files for local development:

```bash
# .env
SPATIALISE_API_KEY=your-api-key-here
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379/0
```

Load with `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env

api_key = os.environ['SPATIALISE_API_KEY']
```

### AWS Secrets Manager

Retrieve secrets from AWS Secrets Manager:

```python
import boto3
import json
from spatialise import SpatialiseSoilPrediction

def get_secret(secret_name, region_name='us-east-1'):
    """Retrieve secret from AWS Secrets Manager.

    Parameters
    ----------
    secret_name : str
        Name of the secret in Secrets Manager.
    region_name : str, default='us-east-1'
        AWS region.

    Returns
    -------
    dict
        Secret value as dictionary.
    """
    client = boto3.client('secretsmanager', region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve secret: {e}")


# Usage
secrets = get_secret('spatialise/api-credentials')
client = SpatialiseSoilPrediction(api_key=secrets['api_key'])
```

### Google Cloud Secret Manager

Retrieve secrets from Google Cloud Secret Manager:

```python
from google.cloud import secretmanager
from spatialise import SpatialiseSoilPrediction

def access_secret_version(project_id, secret_id, version_id='latest'):
    """Access secret version from Google Cloud Secret Manager.

    Parameters
    ----------
    project_id : str
        Google Cloud project ID.
    secret_id : str
        Secret identifier.
    version_id : str, default='latest'
        Secret version.

    Returns
    -------
    str
        Secret value.
    """
    client = secretmanager.SecretManagerServiceClient()

    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})

    return response.payload.data.decode('UTF-8')


# Usage
api_key = access_secret_version(
    project_id='my-project',
    secret_id='spatialise-api-key'
)
client = SpatialiseSoilPrediction(api_key=api_key)
```

### HashiCorp Vault

Retrieve secrets from Vault:

```python
import hvac
from spatialise import SpatialiseSoilPrediction

def get_vault_secret(vault_url, token, secret_path):
    """Retrieve secret from HashiCorp Vault.

    Parameters
    ----------
    vault_url : str
        Vault server URL.
    token : str
        Vault authentication token.
    secret_path : str
        Path to secret in Vault.

    Returns
    -------
    dict
        Secret data.
    """
    client = hvac.Client(url=vault_url, token=token)

    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")

    secret = client.secrets.kv.v2.read_secret_version(path=secret_path)
    return secret['data']['data']


# Usage
secrets = get_vault_secret(
    vault_url='https://vault.example.com',
    token=os.environ['VAULT_TOKEN'],
    secret_path='spatialise/credentials'
)
client = SpatialiseSoilPrediction(api_key=secrets['api_key'])
```

## Database Integration

### PostgreSQL Schema

Track batches and jobs in PostgreSQL:

```sql
-- Batches table
CREATE TABLE batches (
    batch_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    total_jobs INTEGER NOT NULL,
    completed_jobs INTEGER DEFAULT 0,
    failed_jobs INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB
);

-- Jobs table
CREATE TABLE jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    batch_id VARCHAR(255) REFERENCES batches(batch_id),
    status VARCHAR(50) NOT NULL,
    signed_cog_url TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Index for efficient queries
CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_created_at ON batches(created_at);
CREATE INDEX idx_jobs_batch_id ON jobs(batch_id);
CREATE INDEX idx_jobs_status ON jobs(status);
```

### SQLAlchemy Models

Define models with SQLAlchemy:

```python
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Batch(Base):
    """Batch tracking model."""

    __tablename__ = 'batches'

    batch_id = Column(String(255), primary_key=True)
    status = Column(String(50), nullable=False, index=True)
    total_jobs = Column(Integer, nullable=False)
    completed_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    metadata = Column(JSON)

    jobs = relationship("Job", back_populates="batch")


class Job(Base):
    """Job tracking model."""

    __tablename__ = 'jobs'

    job_id = Column(String(255), primary_key=True)
    batch_id = Column(
        String(255),
        ForeignKey('batches.batch_id'),
        index=True
    )
    status = Column(String(50), nullable=False, index=True)
    signed_cog_url = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    batch = relationship("Batch", back_populates="jobs")
```

### Batch Lifecycle Management

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from spatialise import SpatialiseSoilPrediction
from datetime import datetime

class BatchManager:
    """Manage batch lifecycle with database persistence.

    Parameters
    ----------
    client : SpatialiseSoilPrediction
        API client instance.
    db_url : str
        Database connection URL.
    """

    def __init__(self, client, db_url):
        self.client = client
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)

    def create_batch(self, jobs, metadata=None):
        """Create batch and store in database.

        Parameters
        ----------
        jobs : list
            List of prediction jobs.
        metadata : dict, optional
            Batch metadata.

        Returns
        -------
        Batch
            Created batch model.
        """
        session = self.Session()
        try:
            # Create batch via API
            api_batch = self.client.batch.create(
                jobs=jobs,
                metadata=metadata
            )

            # Store in database
            batch = Batch(
                batch_id=api_batch.batch_id,
                status=api_batch.status,
                total_jobs=api_batch.total_jobs,
                metadata=metadata
            )
            session.add(batch)
            session.commit()

            return batch
        finally:
            session.close()

    def update_batch_status(self, batch_id):
        """Update batch status from API.

        Parameters
        ----------
        batch_id : str
            Batch identifier.

        Returns
        -------
        Batch
            Updated batch model.
        """
        session = self.Session()
        try:
            # Fetch status from API
            api_status = self.client.batch.retrieve_status(batch_id)

            # Update database
            batch = session.query(Batch).filter_by(
                batch_id=batch_id
            ).first()

            if batch:
                batch.status = api_status.status
                batch.completed_jobs = api_status.completed_jobs
                batch.failed_jobs = api_status.failed_jobs

                if api_status.status == 'completed':
                    batch.completed_at = datetime.utcnow()

                # Update jobs
                for api_job in api_status.jobs:
                    job = session.query(Job).filter_by(
                        job_id=api_job.job_id
                    ).first()

                    if not job:
                        job = Job(
                            job_id=api_job.job_id,
                            batch_id=batch_id
                        )
                        session.add(job)

                    job.status = api_job.status
                    job.signed_cog_url = api_job.signed_cog_url
                    job.error_message = api_job.error_message

                    if api_job.status in ('completed', 'failed'):
                        job.completed_at = datetime.utcnow()

                session.commit()

            return batch
        finally:
            session.close()

    def get_pending_batches(self):
        """Retrieve all pending batches.

        Returns
        -------
        list of Batch
            Pending batches.
        """
        session = self.Session()
        try:
            return session.query(Batch).filter(
                Batch.status.in_(['pending', 'processing'])
            ).all()
        finally:
            session.close()
```

### MongoDB Schema

Alternative implementation using MongoDB:

```python
from pymongo import MongoClient
from datetime import datetime

class MongoDBBatchManager:
    """Manage batches with MongoDB.

    Parameters
    ----------
    client : SpatialiseSoilPrediction
        API client.
    mongo_uri : str
        MongoDB connection URI.
    database : str, default='spatialise'
        Database name.
    """

    def __init__(self, client, mongo_uri, database='spatialise'):
        self.client = client
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[database]
        self.batches = self.db.batches
        self.jobs = self.db.jobs

        # Create indexes
        self.batches.create_index('batch_id', unique=True)
        self.batches.create_index('status')
        self.batches.create_index('created_at')
        self.jobs.create_index('batch_id')
        self.jobs.create_index('status')

    def create_batch(self, jobs, metadata=None):
        """Create and store batch.

        Parameters
        ----------
        jobs : list
            Prediction jobs.
        metadata : dict, optional
            Batch metadata.

        Returns
        -------
        dict
            Batch document.
        """
        # Create via API
        api_batch = self.client.batch.create(jobs=jobs, metadata=metadata)

        # Store in MongoDB
        batch_doc = {
            'batch_id': api_batch.batch_id,
            'status': api_batch.status,
            'total_jobs': api_batch.total_jobs,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'created_at': datetime.utcnow(),
            'metadata': metadata or {}
        }
        self.batches.insert_one(batch_doc)

        return batch_doc

    def update_batch_status(self, batch_id):
        """Update batch from API status.

        Parameters
        ----------
        batch_id : str
            Batch identifier.

        Returns
        -------
        dict
            Updated batch document.
        """
        # Fetch from API
        api_status = self.client.batch.retrieve_status(batch_id)

        # Update batch
        update_data = {
            'status': api_status.status,
            'completed_jobs': api_status.completed_jobs,
            'failed_jobs': api_status.failed_jobs,
            'updated_at': datetime.utcnow()
        }

        if api_status.status == 'completed':
            update_data['completed_at'] = datetime.utcnow()

        self.batches.update_one(
            {'batch_id': batch_id},
            {'$set': update_data}
        )

        # Update jobs
        for api_job in api_status.jobs:
            job_doc = {
                'job_id': api_job.job_id,
                'batch_id': batch_id,
                'status': api_job.status,
                'signed_cog_url': api_job.signed_cog_url,
                'error_message': api_job.error_message,
                'updated_at': datetime.utcnow()
            }

            if api_job.status in ('completed', 'failed'):
                job_doc['completed_at'] = datetime.utcnow()

            self.jobs.update_one(
                {'job_id': api_job.job_id},
                {'$set': job_doc},
                upsert=True
            )

        return self.batches.find_one({'batch_id': batch_id})
```

## Asynchronous Processing

### Celery Task Queue

Process batches asynchronously with Celery:

```python
from celery import Celery
from spatialise import SpatialiseSoilPrediction
import time

# Configure Celery
app = Celery(
    'spatialise_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@app.task(bind=True, max_retries=3)
def submit_batch_task(self, jobs, metadata=None):
    """Submit batch as Celery task.

    Parameters
    ----------
    jobs : list
        Prediction jobs.
    metadata : dict, optional
        Batch metadata.

    Returns
    -------
    dict
        Result containing batch_id.
    """
    try:
        client = SpatialiseSoilPrediction()
        batch = client.batch.create(jobs=jobs, metadata=metadata)

        return {
            'batch_id': batch.batch_id,
            'status': batch.status,
            'total_jobs': batch.total_jobs
        }
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@app.task
def poll_batch_status_task(batch_id, interval=30, timeout=3600):
    """Poll batch status until completion.

    Parameters
    ----------
    batch_id : str
        Batch identifier.
    interval : int, default=30
        Polling interval in seconds.
    timeout : int, default=3600
        Maximum wait time in seconds.

    Returns
    -------
    dict
        Final batch status.
    """
    client = SpatialiseSoilPrediction()
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Batch {batch_id} timeout after {timeout}s")

        status = client.batch.retrieve_status(batch_id)

        if status.status == 'completed':
            return {
                'batch_id': status.batch_id,
                'status': status.status,
                'completed_jobs': status.completed_jobs,
                'failed_jobs': status.failed_jobs
            }

        time.sleep(interval)


# Usage
result = submit_batch_task.delay(jobs=[...], metadata={...})
batch_info = result.get(timeout=10)
print(f"Batch submitted: {batch_info['batch_id']}")
```

### AWS SQS Queue Integration

Process batches with AWS SQS:

```python
import boto3
import json
from spatialise import SpatialiseSoilPrediction

class SQSBatchProcessor:
    """Process batch requests from SQS queue.

    Parameters
    ----------
    queue_url : str
        SQS queue URL.
    region_name : str, default='us-east-1'
        AWS region.
    """

    def __init__(self, queue_url, region_name='us-east-1'):
        self.sqs = boto3.client('sqs', region_name=region_name)
        self.queue_url = queue_url
        self.client = SpatialiseSoilPrediction()

    def send_batch_request(self, jobs, metadata=None):
        """Send batch request to queue.

        Parameters
        ----------
        jobs : list
            Prediction jobs.
        metadata : dict, optional
            Batch metadata.

        Returns
        -------
        dict
            SQS message response.
        """
        message_body = json.dumps({
            'jobs': jobs,
            'metadata': metadata
        })

        return self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=message_body
        )

    def process_messages(self, max_messages=10):
        """Process messages from queue.

        Parameters
        ----------
        max_messages : int, default=10
            Maximum messages to process per call.

        Returns
        -------
        list
            Created batches.
        """
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20
        )

        batches = []
        for message in response.get('Messages', []):
            try:
                # Parse message
                body = json.loads(message['Body'])
                jobs = body['jobs']
                metadata = body.get('metadata')

                # Create batch
                batch = self.client.batch.create(
                    jobs=jobs,
                    metadata=metadata
                )
                batches.append(batch)

                # Delete message
                self.sqs.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=message['ReceiptHandle']
                )

            except Exception as e:
                # Handle error (could move to DLQ)
                print(f"Error processing message: {e}")

        return batches
```

## Logging and Monitoring

### Structured Logging

Implement structured logging with `structlog`:

```python
import structlog
from spatialise import SpatialiseSoilPrediction

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def create_batch_with_logging(client, jobs, metadata=None):
    """Create batch with structured logging.

    Parameters
    ----------
    client : SpatialiseSoilPrediction
        API client.
    jobs : list
        Prediction jobs.
    metadata : dict, optional
        Batch metadata.

    Returns
    -------
    BatchCreateResponse
        Created batch.
    """
    logger.info(
        "batch_create_initiated",
        job_count=len(jobs),
        metadata=metadata
    )

    try:
        batch = client.batch.create(jobs=jobs, metadata=metadata)

        logger.info(
            "batch_created",
            batch_id=batch.batch_id,
            status=batch.status,
            total_jobs=batch.total_jobs
        )

        return batch

    except Exception as e:
        logger.error(
            "batch_create_failed",
            error=str(e),
            error_type=type(e).__name__,
            job_count=len(jobs)
        )
        raise
```

### Application Performance Monitoring

Integrate with APM tools:

```python
# Datadog APM
from ddtrace import tracer
from spatialise import SpatialiseSoilPrediction

@tracer.wrap(service="spatialise-api", resource="batch.create")
def create_batch_monitored(client, jobs, metadata=None):
    """Create batch with Datadog tracing."""
    with tracer.trace("spatialise.batch.create") as span:
        span.set_tag("job_count", len(jobs))
        batch = client.batch.create(jobs=jobs, metadata=metadata)
        span.set_tag("batch_id", batch.batch_id)
        return batch


# New Relic
import newrelic.agent
from spatialise import SpatialiseSoilPrediction

@newrelic.agent.function_trace()
def create_batch_traced(client, jobs, metadata=None):
    """Create batch with New Relic tracing."""
    newrelic.agent.add_custom_parameter("job_count", len(jobs))

    batch = client.batch.create(jobs=jobs, metadata=metadata)

    newrelic.agent.add_custom_parameter("batch_id", batch.batch_id)
    newrelic.agent.add_custom_parameter("total_jobs", batch.total_jobs)

    return batch
```

## Error Recovery

### Circuit Breaker Pattern

Prevent cascading failures with circuit breaker:

```python
from enum import Enum
import time
import threading

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """Circuit breaker for API calls.

    Parameters
    ----------
    failure_threshold : int, default=5
        Failures before opening circuit.
    timeout : float, default=60
        Seconds before attempting recovery.
    """

    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """Execute function through circuit breaker.

        Parameters
        ----------
        func : callable
            Function to call.
        *args
            Positional arguments.
        **kwargs
            Keyword arguments.

        Returns
        -------
        Any
            Function result.

        Raises
        ------
        Exception
            If circuit is open or function fails.
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                if (time.time() - self.last_failure_time) > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            with self.lock:
                self.failure_count = 0
                self.state = CircuitState.CLOSED

            return result

        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN

            raise


# Usage
circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
client = SpatialiseSoilPrediction()

def create_batch_protected(jobs, metadata=None):
    return circuit_breaker.call(
        client.batch.create,
        jobs=jobs,
        metadata=metadata
    )
```

### Dead Letter Queue

Handle failed messages with DLQ:

```python
import json
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FailedRequest:
    """Failed request record."""
    request_data: dict
    error_message: str
    timestamp: datetime
    retry_count: int

class DeadLetterQueue:
    """Manage failed batch requests.

    Parameters
    ----------
    storage_path : str
        Path to store failed requests.
    max_retries : int, default=3
        Maximum retry attempts.
    """

    def __init__(self, storage_path, max_retries=3):
        self.storage_path = storage_path
        self.max_retries = max_retries
        self.failed_requests = []

    def add_failed_request(self, jobs, metadata, error):
        """Add failed request to DLQ.

        Parameters
        ----------
        jobs : list
            Original job list.
        metadata : dict
            Original metadata.
        error : Exception
            Error that occurred.
        """
        failed_req = FailedRequest(
            request_data={'jobs': jobs, 'metadata': metadata},
            error_message=str(error),
            timestamp=datetime.utcnow(),
            retry_count=0
        )
        self.failed_requests.append(failed_req)
        self._persist()

    def retry_failed_requests(self, client):
        """Retry all failed requests.

        Parameters
        ----------
        client : SpatialiseSoilPrediction
            API client.

        Returns
        -------
        dict
            Retry results.
        """
        results = {'succeeded': [], 'failed': []}

        for req in self.failed_requests[:]:
            if req.retry_count >= self.max_retries:
                continue

            try:
                batch = client.batch.create(**req.request_data)
                results['succeeded'].append(batch.batch_id)
                self.failed_requests.remove(req)
            except Exception as e:
                req.retry_count += 1
                req.error_message = str(e)
                results['failed'].append(req)

        self._persist()
        return results

    def _persist(self):
        """Persist DLQ to disk."""
        with open(self.storage_path, 'w') as f:
            data = [
                {
                    'request_data': req.request_data,
                    'error_message': req.error_message,
                    'timestamp': req.timestamp.isoformat(),
                    'retry_count': req.retry_count
                }
                for req in self.failed_requests
            ]
            json.dump(data, f, indent=2)
```

## See Also

- [Webhook Integration](./webhooks.md) - Production webhook handlers
- [Idempotency](./idempotency.md) - Database-backed idempotency
- [Rate Limiting](./rate-limiting.md) - Queue-based rate limiting
- [GeoTIFF Processing](./geotiff-processing.md) - Result processing pipelines

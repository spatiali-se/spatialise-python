# This file is part of the spatialise SDK and is maintained by hand.

from typing import Dict
from datetime import datetime

from .._models import BaseModel
from .batch_status import BatchStatus

__all__ = ["BatchCreateResponse"]


class BatchCreateResponse(BaseModel):
    batch_id: str
    """Unique identifier for the batch"""

    created_at: datetime
    """Batch creation timestamp"""

    job_ids: Dict[str, str]
    """Mapping of job indices to job IDs"""

    message: str
    """Status message"""

    status: BatchStatus
    """Current status of the batch"""

    total_jobs: int
    """Total number of jobs in the batch"""

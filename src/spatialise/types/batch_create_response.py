# This file is part of the spatialise SDK and is maintained by hand.

from typing import Dict
from datetime import datetime

from pydantic import Field

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

    total_jobs: int = Field(alias="total_tasks")
    """Total number of jobs in the batch (wire field: ``total_tasks``)."""

    @property
    def total_tasks(self) -> int:
        """Wire-name alias for :attr:`total_jobs`."""
        return self.total_jobs

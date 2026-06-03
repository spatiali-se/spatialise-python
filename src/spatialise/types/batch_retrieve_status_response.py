# This file is part of the spatialise SDK and is maintained by hand.

from typing import List, Optional
from datetime import datetime
from typing_extensions import Literal

from pydantic import Field

from .._models import BaseModel
from .batch_status import BatchStatus

__all__ = ["BatchRetrieveStatusResponse", "Job"]


class Job(BaseModel):
    created_at: datetime
    """Job creation timestamp"""

    job_id: str
    """Unique identifier for the job"""

    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    """Current status of the job"""

    updated_at: datetime
    """Last update timestamp"""

    error_message: Optional[str] = None
    """Error message if job failed"""

    signed_cog_url: Optional[str] = None
    """Temporary signed URL to download result Cloud Optimized GeoTIFF (COG).

    Valid for 6 hours.
    """

    signed_cog_url_created_at: Optional[datetime] = None
    """UTC timestamp when the signed COG URL was generated"""


class BatchRetrieveStatusResponse(BaseModel):
    batch_id: str
    """Unique identifier for the batch"""

    # The API serializes these counts as ``*_tasks`` on the wire. They are exposed
    # here under the historical ``*_jobs`` names (via alias) so existing callers keep
    # working unchanged; each also has a ``*_tasks`` property that returns the same
    # value for callers who prefer the wire name.
    completed_jobs: int = Field(alias="completed_tasks")
    """Number of completed jobs (wire field: ``completed_tasks``)."""

    created_at: datetime
    """Batch creation timestamp"""

    failed_jobs: int = Field(alias="failed_tasks")
    """Number of failed jobs (wire field: ``failed_tasks``)."""

    has_more: bool
    """Whether there are more jobs to fetch"""

    jobs: List[Job]
    """Status of individual jobs"""

    pending_jobs: int = Field(alias="pending_tasks")
    """Number of pending jobs (wire field: ``pending_tasks``)."""

    status: BatchStatus
    """Current status of the batch"""

    total_jobs: int = Field(alias="total_tasks")
    """Total number of jobs in the batch (wire field: ``total_tasks``)."""

    updated_at: datetime
    """Last update timestamp"""

    next_cursor: Optional[str] = None
    """Cursor for fetching the next page. Null if no more pages."""

    @property
    def total_tasks(self) -> int:
        """Wire-name alias for :attr:`total_jobs`."""
        return self.total_jobs

    @property
    def completed_tasks(self) -> int:
        """Wire-name alias for :attr:`completed_jobs`."""
        return self.completed_jobs

    @property
    def failed_tasks(self) -> int:
        """Wire-name alias for :attr:`failed_jobs`."""
        return self.failed_jobs

    @property
    def pending_tasks(self) -> int:
        """Wire-name alias for :attr:`pending_jobs`."""
        return self.pending_jobs

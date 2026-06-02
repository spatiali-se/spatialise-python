# This file is part of the spatialise SDK and is maintained by hand.

from typing import List, Optional
from datetime import datetime
from typing_extensions import Literal

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

    # NOTE: field names below are provisional. The backend (geo_batch_dispatcher;
    # see SPA-1758, which models the entity as "PatchBatch") owns the wire shape —
    # confirm these names against its status response before cutting 0.3.0.
    total_patch_batches: Optional[int] = None
    """Total number of patch-batches this job decomposes into.

    A job (1:1 with a COG) is processed as many patch-batches in the V2 pipeline.
    None when the backend does not report patch-batch progress for this job.
    """

    completed_patch_batches: Optional[int] = None
    """Number of patch-batches completed so far for this job.

    Together with ``total_patch_batches`` this lets callers show progress before
    the job's COG is ready. None when patch-batch progress is unavailable.
    """


class BatchRetrieveStatusResponse(BaseModel):
    batch_id: str
    """Unique identifier for the batch"""

    completed_jobs: int
    """Number of completed jobs"""

    created_at: datetime
    """Batch creation timestamp"""

    failed_jobs: int
    """Number of failed jobs"""

    has_more: bool
    """Whether there are more jobs to fetch"""

    jobs: List[Job]
    """Status of individual jobs"""

    pending_jobs: int
    """Number of pending jobs"""

    status: BatchStatus
    """Current status of the batch"""

    total_jobs: int
    """Total number of jobs in the batch"""

    updated_at: datetime
    """Last update timestamp"""

    next_cursor: Optional[str] = None
    """Cursor for fetching the next page. Null if no more pages."""

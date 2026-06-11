# This file is part of the spatialise SDK and is maintained by hand.

from typing import List, Optional
from datetime import datetime

from .._models import BaseModel
from .patch_batch_status_info import JobStatusLiteral, PatchBatchStatusInfo

__all__ = ["JobDetailStatusResponse"]


class JobDetailStatusResponse(BaseModel):
    """A single job's status, COG info, fan-in counters, and a page of patch-batches.

    Returned by ``client.batch.retrieve_job_status``. Surfaces V2 patch-batch
    progress (``total_patch_batches`` / ``completed_patch_batches``) plus a
    paginated list of per-patch-batch statuses.
    """

    job_id: str
    """Unique identifier for the job"""

    created_at: datetime
    """Job creation timestamp"""

    updated_at: datetime
    """Last update timestamp"""

    has_more: bool
    """Whether more patch-batches remain beyond this page"""

    patch_batches: List[PatchBatchStatusInfo]
    """Page of per-patch-batch statuses, ascending by index"""

    status: Optional[JobStatusLiteral] = None
    """Current job status; null if not yet written"""

    error_message: Optional[str] = None
    """Error message if the job failed"""

    signed_cog_url: Optional[str] = None
    """Temporary signed URL to the result COG, if ready"""

    signed_cog_url_created_at: Optional[datetime] = None
    """UTC timestamp when the signed COG URL was generated"""

    total_patch_batches: Optional[int] = None
    """Total patch-batches for the job; null until seeded"""

    completed_patch_batches: Optional[int] = None
    """Completed patch-batches for the job; null until seeded"""

    next_cursor: Optional[str] = None
    """Opaque cursor for the next patch-batches page; null if none remain"""

# This file is part of the spatialise SDK and is maintained by hand.

from typing import Optional
from datetime import datetime
from typing_extensions import Literal, TypeAlias

from .._models import BaseModel

__all__ = ["PatchBatchStatusInfo", "JobStatusLiteral"]

JobStatusLiteral: TypeAlias = Literal[
    "pending",
    "running",
    "processing_complete",
    "completed",
    "failed",
    "partially_failed",
    "cancelled",
]
"""Status of a job or patch-batch in the V2 inference pipeline.

Wider than the batch-status ``Job.status`` (5 values): the map-reduce flow adds
``processing_complete`` and ``partially_failed``.
"""


class PatchBatchStatusInfo(BaseModel):
    """Status of a single patch-batch mini-job within a job.

    Used both as an element of a job's ``patch_batches`` list and as the response
    of the single-patch-batch status endpoint. Deliberately omits heavy prediction
    payloads — this is a status surface.
    """

    patch_batch_idx: int
    """Patch-batch index within the job"""

    created_at: datetime
    """Patch-batch creation timestamp"""

    updated_at: datetime
    """Last update timestamp"""

    status: Optional[JobStatusLiteral] = None
    """Current status; null if the patch-batch status has not been written yet"""

    point_count: Optional[int] = None
    """Number of points in this patch-batch"""

    inference_duration_ms: Optional[int] = None
    """Inference duration in milliseconds"""

    failure_reason: Optional[str] = None
    """Failure reason when the patch-batch failed"""

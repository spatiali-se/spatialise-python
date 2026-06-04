# This file is part of the spatialise SDK and is maintained by hand.

from __future__ import annotations

from typing_extensions import TypeAlias

from .cursor_pagination_params import CursorPaginationParams

__all__ = ["JobRetrieveStatusParams"]

# The job-detail endpoint paginates its patch_batches list with the same
# cursor/limit scheme as the batch-status endpoint.
JobRetrieveStatusParams: TypeAlias = CursorPaginationParams

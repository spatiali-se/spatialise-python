# This file is part of the spatialise SDK and is maintained by hand.

from __future__ import annotations

from typing_extensions import TypeAlias

from .cursor_pagination_params import CursorPaginationParams

__all__ = ["BatchRetrieveStatusParams"]

# The batch-status endpoint paginates its jobs list with cursor/limit.
BatchRetrieveStatusParams: TypeAlias = CursorPaginationParams

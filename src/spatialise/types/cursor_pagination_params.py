# This file is part of the spatialise SDK and is maintained by hand.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

__all__ = ["CursorPaginationParams"]


class CursorPaginationParams(TypedDict, total=False):
    """Shared cursor pagination query params (``cursor`` + ``limit``)."""

    cursor: Optional[str]

    limit: int

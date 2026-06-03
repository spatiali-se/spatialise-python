# This file is part of the spatialise SDK and is maintained by hand.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

__all__ = ["JobRetrieveStatusParams"]


class JobRetrieveStatusParams(TypedDict, total=False):
    cursor: Optional[str]

    limit: int

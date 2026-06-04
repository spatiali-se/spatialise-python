# This file is part of the spatialise SDK and is maintained by hand.

from typing_extensions import Literal, TypeAlias

__all__ = ["BatchStatus"]

BatchStatus: TypeAlias = Literal["created", "processing", "completed", "failed", "partially_failed"]

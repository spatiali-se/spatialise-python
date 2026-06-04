# This file is part of the spatialise SDK and is maintained by hand.

from typing import Dict
from typing_extensions import TypeAlias

__all__ = ["HealthCheckResponse"]

HealthCheckResponse: TypeAlias = Dict[str, str]

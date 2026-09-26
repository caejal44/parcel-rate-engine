from datetime import date
from enum import Enum

from pydantic import BaseModel


class FuelType(str, Enum):
    DIESEL = "DIESEL"
    JET = "JET"


class FuelPrice(BaseModel):
    fuel_type: FuelType
    value: float
    effective_date: date
    units: str
from datetime import date, datetime

from pydantic import BaseModel

from src.service_quote.fuel.schemas import FuelType


class QuoteCharge(BaseModel):
    charge_code: str
    charge_description: str
    amount: float
    fuel_applied: bool


class ServiceQuoteResponse(BaseModel):
    quote_id: str
    shipment_id: str
    billable_shipment_id: str

    carrier_service_code: str
    carrier_code: str
    carrier_name: str
    service_code: str
    service_name: str

    zone: int
    billable_weight: int

    transportation_charge: float
    charges: list[QuoteCharge]

    fuel_type: FuelType
    fuel_price: float
    fuel_effective_date: date
    fuel_pct: float
    fuel_charge: float

    total_charge: float
    estimated_delivery: datetime
    created_at: datetime
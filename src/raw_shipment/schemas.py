from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CreateRawShipmentRequest(BaseModel):
    orig_zip: str = Field(pattern=r"^\d{5}$")
    dest_zip: str = Field(pattern=r"^\d{5}$")
    ship_date: datetime = Field(...)
    requested_delivery: datetime = Field(...)

    actual_weight: float = Field(gt=0, le=1500)
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)

    declared_value: float = Field(default=0.0, ge=0)
    residential_delivery: bool
    reference: str | None = None
    signature_required: bool = False
    adult_signature_required: bool = False
    additional_handling_packaging: bool = False
    saturday_delivery: bool = False

    @model_validator(mode="after")
    def validate_dates(self):
            if self.ship_date >= self.requested_delivery:
                raise ValueError("requested_delivery cannot be on or before ship_date")
            return self

class RawShipmentResponse(BaseModel):
    shipment_id: str
    user_id: str
    orig_zip: str
    dest_zip: str
    requested_delivery: datetime
    ship_date: datetime
    actual_weight: float
    length: float
    width: float
    height: float
    declared_value: float
    residential_delivery: bool
    reference: str | None
    signature_required: bool
    adult_signature_required: bool
    additional_handling_packaging: bool
    saturday_delivery: bool
    created_at: datetime

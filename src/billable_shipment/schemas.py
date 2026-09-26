from datetime import datetime

from pydantic import BaseModel

from src.common.enums import SignatureType, LargePackageType, DeliveryAreaType, AdditionalHandlingType


class CreateBillableShipment(BaseModel):
    shipment_id: str

    carrier_service_code: str
    carrier_code: str
    service_code: str

    zone: int
    billable_weight: int

    residential_delivery: bool
    signature_required_type: SignatureType | None = None
    saturday_delivery: bool = False
    declared_value: float
    additional_handling_type: AdditionalHandlingType | None = None
    large_package_type: LargePackageType | None = None
    delivery_area_type: DeliveryAreaType | None = None
    estimated_delivery: datetime

    reference: str | None = None

class BillableShipmentResponse(CreateBillableShipment):
    billable_shipment_id: str
    created_at: datetime

from src.common.exceptions import NotFoundError
from src.common.utils import create_id, get_timestamp
from src.raw_shipment.repository import save_raw_shipment, get_raw_shipment

from src.raw_shipment.schemas import RawShipmentResponse, CreateRawShipmentRequest


def create_raw_shipment(request: CreateRawShipmentRequest, user_id: str) -> RawShipmentResponse:
    raw_shipment = {
        "shipment_id": create_id(),
        "user_id": user_id,
        "orig_zip": request.orig_zip,
        "dest_zip": request.dest_zip,
        "requested_delivery": request.requested_delivery,
        "ship_date": request.ship_date,
        "actual_weight": request.actual_weight,
        "length": request.length,
        "width": request.width,
        "height": request.height,
        "declared_value": request.declared_value,
        "residential_delivery": request.residential_delivery,
        "reference": request.reference,
        "signature_required": request.signature_required,
        "adult_signature_required": request.adult_signature_required,
        "additional_handling_packaging": request.additional_handling_packaging,
        "saturday_delivery": request.saturday_delivery,
        "created_at": get_timestamp(),
    }
    save_raw_shipment(raw_shipment)
    return RawShipmentResponse(**raw_shipment)

def get_raw_shipment_by_id(shipment_id: str, user_id: str) -> RawShipmentResponse:
    raw_shipment = get_raw_shipment(shipment_id)
    if raw_shipment is None:
        raise NotFoundError("shipment not found")
    if user_id != raw_shipment["user_id"]:
        raise NotFoundError("shipment not found")
    return RawShipmentResponse(**raw_shipment)


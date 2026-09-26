from src.common.responses import success_response, error_response
from src.common.utils import get_current_user_id, error_handler, get_required_path_param
from src.billable_shipment.service import create_billable_shipments
from src.raw_shipment.service import get_raw_shipment_by_id


@error_handler
def lambda_handler(event, context):
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")

    user_id = get_current_user_id(event)

    if method == "POST":
        shipment_id = get_required_path_param(event, "shipment_id")
        raw_shipment = get_raw_shipment_by_id(shipment_id, user_id)
        billable_shipments = create_billable_shipments(raw_shipment)
        return success_response(201, {
        "billable_shipments": [
            shipment.model_dump(mode="json")
            for shipment in billable_shipments]})

    else:
        return error_response(405, "method_not_allowed")

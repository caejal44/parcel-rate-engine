import json

from src.common.responses import success_response, error_response
from src.common.utils import get_current_user_id, error_handler
from src.raw_shipment.schemas import CreateRawShipmentRequest
from src.raw_shipment.service import create_raw_shipment


@error_handler
def lambda_handler(event, context):
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")

    user_id = get_current_user_id(event)

    if method == "POST":
        body = json.loads(event.get("body") or "{}")
        request = CreateRawShipmentRequest(**body)
        raw_shipment = create_raw_shipment(request, user_id)
        return success_response(201, raw_shipment.model_dump(mode="json"))

    else:
        return error_response(405, "method_not_allowed")


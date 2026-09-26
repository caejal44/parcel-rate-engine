from src.common.responses import success_response, error_response
from src.common.utils import get_current_user_id, get_required_path_param, error_handler
from src.service_quote.service import create_service_quotes


@error_handler
def lambda_handler(event, context):
    method = event.get("httpMethod") or event.get(
        "requestContext", {}
    ).get("http", {}).get("method")

    user_id = get_current_user_id(event)

    if method == "POST":
        shipment_id = get_required_path_param(event, "shipment_id")
        quotes = create_service_quotes(shipment_id, user_id)

        return success_response(
            201,
            {
                "quotes": [
                    quote.model_dump(mode="json")
                    for quote in quotes
                ]
            }
        )

    else:
        return error_response(405, "method_not_allowed")
import json

from src.billable_shipment.handler import lambda_handler


def test_create_billable_shipments_success():

    shipment_id = "11357b84-b5a6-40fa-9278-b4f83382c50c"

    event = {
        "httpMethod": "POST",
        "pathParameters": {
            "shipment_id": shipment_id
        }
    }

    response = lambda_handler(event, None)

    print(json.dumps(response, indent=2))

    assert response["statusCode"] == 201

    body = json.loads(response["body"])

    print(json.dumps(body, indent=2))

    billable_shipments = body["billable_shipments"]

    assert len(billable_shipments) > 0

    for billable_shipment in billable_shipments:
        assert billable_shipment["shipment_id"] == shipment_id
        print(json.dumps(billable_shipment, indent=2))


if __name__ == "__main__":
    test_create_billable_shipments_success()
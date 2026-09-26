from src.raw_shipment.handler import lambda_handler
import json



def test_create_raw_shipment_success():

    test_data = {
        "orig_zip": "80201",
        "dest_zip": "99361",
        "requested_delivery": "2026-08-28T18:00:00",
        "ship_date": "2026-08-24T18:00:00",
        "actual_weight": 61.0,
        "length": 49.0,
        "width": 12.0,
        "height": 12.0,
        "declared_value": 300.0,
        "residential_delivery": False,
        "reference": "431203949",
        "signature_required": False,
        "adult_signature_required": True,
        "additional_handling_packaging": True,
        "saturday_delivery": False,
    }

    event = {
        "httpMethod": "POST",
        "body": json.dumps(
            test_data
        )
    }


    response = lambda_handler(event, None)

    print("Response:", response)

    assert response["statusCode"] == 201

    body = json.loads(response["body"])


    assert body["length"] == 49.0
    assert body["dest_zip"] == "99361"
    assert body["actual_weight"] == 61.0
    assert body["requested_delivery"] == "2026-08-28T18:00:00"


if __name__ == "__main__":
    test_create_raw_shipment_success()
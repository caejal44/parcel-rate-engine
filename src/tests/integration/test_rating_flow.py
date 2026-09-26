import json

from src.raw_shipment.handler import lambda_handler as raw_shipment_handler
from src.billable_shipment.handler import lambda_handler as billable_shipment_handler
from src.service_quote.handler import lambda_handler as service_quote_handler


def test_complete_rating_flow():

    # =========================================================
    # 1. CREATE RAW SHIPMENT
    # =========================================================

    test_data = {
        "orig_zip": "30305",
        "dest_zip": "18103",
        "requested_delivery": "2026-09-25T18:00:00",
        "ship_date": "2026-09-19T18:00:00",
        "actual_weight": 50.0,
        "length": 109.0,
        "width": 10.0,
        "height": 10.0,
        "declared_value": 301.0,
        "residential_delivery": False,
        "reference": "E2E-TEST-001",
        "signature_required": True,
        "adult_signature_required": False,
        "additional_handling_packaging": True,
        "saturday_delivery": False,
    }

    raw_event = {
        "httpMethod": "POST",
        "body": json.dumps(test_data)
    }

    raw_response = raw_shipment_handler(raw_event, None)

    assert raw_response["statusCode"] == 201

    raw_body = json.loads(raw_response["body"])

    # THIS is the important part:
    # Capture the ID that was just generated.
    shipment_id = raw_body["shipment_id"]

    assert shipment_id is not None
    assert raw_body["actual_weight"] == 50.0
    assert raw_body["dest_zip"] == "18103"

    print("\n========================================")
    print("RAW SHIPMENT")
    print("========================================")
    print(json.dumps(raw_body, indent=2))


    # =========================================================
    # 2. CREATE BILLABLE SHIPMENTS
    # =========================================================

    billable_event = {
        "httpMethod": "POST",
        "pathParameters": {
            "shipment_id": shipment_id
        }
    }

    billable_response = billable_shipment_handler(
        billable_event,
        None
    )

    assert billable_response["statusCode"] == 201

    billable_body = json.loads(
        billable_response["body"]
    )

    billable_shipments = billable_body["billable_shipments"]

    assert len(billable_shipments) > 0

    for billable_shipment in billable_shipments:
        assert billable_shipment["shipment_id"] == shipment_id

    print("\n========================================")
    print("BILLABLE SHIPMENTS")
    print("========================================")

    for billable_shipment in billable_shipments:
        print(json.dumps(billable_shipment, indent=2))


    # =========================================================
    # 3. CREATE SERVICE QUOTES
    # =========================================================

    quote_event = {
        "httpMethod": "POST",
        "pathParameters": {
            "shipment_id": shipment_id
        }
    }

    quote_response = service_quote_handler(
        quote_event,
        None
    )

    assert quote_response["statusCode"] == 201

    quote_body = json.loads(
        quote_response["body"]
    )

    quotes = quote_body["quotes"]

    assert len(quotes) > 0

    print("\n========================================")
    print("SERVICE QUOTES")
    print("========================================")

    for quote in quotes:

        assert quote["shipment_id"] == shipment_id
        assert quote["transportation_charge"] > 0
        assert quote["total_charge"] > 0

        # Verify quote math
        accessorial_total = sum(
            charge["amount"]
            for charge in quote["charges"]
        )

        expected_total = round(
            quote["transportation_charge"]
            + accessorial_total
            + quote["fuel_charge"],
            2
        )

        assert quote["total_charge"] == expected_total

        print(json.dumps(quote, indent=2))


    # =========================================================
    # FINAL FLOW CHECK
    # =========================================================

    print("\n========================================")
    print("RATING FLOW COMPLETE")
    print("========================================")

    print(f"Shipment ID: {shipment_id}")
    print(f"Billable shipments: {len(billable_shipments)}")
    print(f"Quotes: {len(quotes)}")
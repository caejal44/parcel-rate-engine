from datetime import date

import pandas as pd

from src.billable_shipment.schemas import BillableShipmentResponse
from src.service_quote.fuel.schemas import FuelPrice, FuelType
from src.service_quote.service import create_service_quote


def test_create_service_quote(monkeypatch):
    # Arrange
    billable_shipment = BillableShipmentResponse(
        billable_shipment_id="billable-123",
        shipment_id="shipment-123",
        carrier_service_code="0101",
        carrier_code="01",
        service_code="01",
        zone=4,
        billable_weight=25,
        residential_delivery=True,
        signature_required_type=None,
        saturday_delivery=False,
        declared_value=0,
        additional_handling_type=None,
        large_package_type=None,
        delivery_area_type=None,
        reference=None,
        created_at="2026-09-19T10:00:00+00:00"
    )

    service_configuration = pd.DataFrame([
        {
            "carrier_service_code": "0101",
            "carrier_name": "PartnerLine Logistics",
            "service_name": "Ground",
            "transport_mode": "ROAD"
        }
    ])

    transportation_rates = pd.DataFrame([
        {
            "carrier_service_code": "0101",
            "zone": 4,
            "billable_weight": 25,
            "net_rate": 20.00
        }
    ])

    charge_rates = pd.DataFrame([
        {
            "carrier_service_code": "0101",
            "charge_code": "RES",
            "charge_description": "Residential Surcharge",
            "net_charge": 5.00,
            "fuel_applied": True
        }
    ])

    fuel_chart = pd.DataFrame([
        {
            "carrier_code": "01",
            "transport_mode": "ROAD",
            "fuel_price_min": 0.00,
            "fuel_pct": 0.10
        },
        {
            "carrier_code": "01",
            "transport_mode": "ROAD",
            "fuel_price_min": 5.00,
            "fuel_pct": 0.20
        }
    ])

    class ReferenceData:
        pass

    reference_data = ReferenceData()
    reference_data.service_configuration = service_configuration
    reference_data.transportation_rates = transportation_rates
    reference_data.charge_rates = charge_rates
    reference_data.fuel_chart = fuel_chart

    fuel_price = FuelPrice(
        fuel_type=FuelType.DIESEL,
        value=5.50,
        effective_date=date(2026, 9, 14),
        units="$/GAL"
    )

    monkeypatch.setattr(
        "src.service_quote.service.get_latest_fuel_price",
        lambda fuel_type: fuel_price
    )

    # Prevent the test from actually writing to DynamoDB
    saved_quotes = []

    monkeypatch.setattr(
        "src.service_quote.service.save_service_quote",
        lambda quote: saved_quotes.append(quote)
    )

    # Act
    quote = create_service_quote(
        billable_shipment,
        reference_data
    )

    # Assert
    assert quote.shipment_id == "shipment-123"
    assert quote.carrier_service_code == "0101"

    assert quote.transportation_charge == 20.00

    assert len(quote.charges) == 1
    assert quote.charges[0].charge_code == "RES"
    assert quote.charges[0].amount == 5.00

    assert quote.fuel_type == FuelType.DIESEL
    assert quote.fuel_price == 5.50
    assert quote.fuel_pct == 0.20

    # Fuel applies to transportation + residential:
    # (20 + 5) * .20 = 5
    assert quote.fuel_charge == 5.00

    # 20 transportation + 5 residential + 5 fuel
    assert quote.total_charge == 30.00

    # Verify persistence was attempted
    assert len(saved_quotes) == 1
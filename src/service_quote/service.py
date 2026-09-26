import math

import pandas as pd

from src.billable_shipment.schemas import BillableShipmentResponse
from src.billable_shipment.service import get_billable_shipments_by_shipment_id
from src.common.enums import DeliveryAreaType, SignatureType, LargePackageType, AdditionalHandlingType
from src.common.exceptions import BadRequestError
from src.common.reference_data import get_reference_data, ReferenceData
from src.common.utils import create_id, get_timestamp
from src.raw_shipment.service import get_raw_shipment_by_id
from src.service_quote.fuel.repository import get_latest_fuel_price
from src.service_quote.fuel.schemas import FuelType, FuelPrice
from src.service_quote.repository import save_service_quote
from src.service_quote.schemas import ServiceQuoteResponse, QuoteCharge

MAX_BILLABLE_WEIGHT = 200

def get_service_name(carrier_service_code: str, service_configuration: pd.DataFrame) -> str:
    match = service_configuration.loc[
        service_configuration["carrier_service_code"] == carrier_service_code,
        "service_name"]

    if match.empty:
        raise Exception(f"No service name found for {carrier_service_code}")

    service_name = match.iloc[0]

    return service_name


def get_carrier_name(carrier_service_code: str, service_configuration: pd.DataFrame) -> str:
    match = service_configuration.loc[
        service_configuration["carrier_service_code"] == carrier_service_code,
        "carrier_name"]

    if match.empty:
        raise Exception(f"No carrier_name found for {carrier_service_code}")

    carrier_name = match.iloc[0]

    return carrier_name

def get_transport_mode(carrier_service_code: str, service_configuration: pd.DataFrame) -> str:
    match = service_configuration.loc[service_configuration["carrier_service_code"] == carrier_service_code,
    "transport_mode"]

    if match.empty:
        raise Exception(f"No transport_mode found for {carrier_service_code}")

    transport_mode = match.iloc[0]

    return transport_mode

def get_transportation_charge(carrier_service_code: str,
                              zone: int,
                              billable_weight: int,
                              transportation_rates: pd.DataFrame) -> float:
    match = transportation_rates.loc[(transportation_rates["carrier_service_code"] == carrier_service_code) &
                                       (transportation_rates["zone"] == zone) &
                                       (transportation_rates["billable_weight"] == billable_weight), "net_rate"]
    if match.empty:
        raise ValueError(f"No net rate found for {carrier_service_code}, zone {zone}, weight {billable_weight}")
    transportation_charge = match.iloc[0]
    return transportation_charge

def get_charge_rate(carrier_service_code: str,
                              charge_code: str,
                              charge_rates: pd.DataFrame) -> QuoteCharge:
    match = charge_rates.loc[(charge_rates["carrier_service_code"] == carrier_service_code) &
                             (charge_rates["charge_code"] == charge_code), ("charge_code",
                                                                      "charge_description",
                                                                      "net_charge",
                                                                      "fuel_applied")]
    if match.empty:
        raise ValueError(f"No {charge_code} rate found for {carrier_service_code}")
    charge = match.iloc[0]
    return QuoteCharge(
        charge_code=charge["charge_code"],
        charge_description=charge["charge_description"],
        amount=charge["net_charge"],
        fuel_applied=charge["fuel_applied"]
    )

def get_fuel_pct(carrier_code: str,
                 transport_mode: str,
                 fuel_price: FuelPrice,
                 fuel_chart: pd.DataFrame) -> float:

    match = fuel_chart.loc[(fuel_chart["carrier_code"] == carrier_code) &
                           (fuel_chart["transport_mode"] == transport_mode) &
                           (fuel_chart["fuel_price_min"] <= fuel_price.value)]

    if match.empty:
        raise ValueError(
            f"No fuel_pct found for carrier {carrier_code}, "
            f"transport_mode {transport_mode}, "
            f"fuel price {fuel_price.value}"
        )

    match = match.sort_values("fuel_price_min", ascending=False)

    return match.iloc[0]["fuel_pct"]

def create_service_quotes(shipment_id: str, user_id: str) -> list[ServiceQuoteResponse]:
    """Create service quotes based on billable shipments."""

    # Confirm shipment exists and belongs to this user.
    get_raw_shipment_by_id(shipment_id, user_id)

    billable_shipments = get_billable_shipments_by_shipment_id(shipment_id)

    # load reference data
    reference_data = get_reference_data()

    service_quotes = []

    for billable_shipment in billable_shipments:
        quote = create_service_quote(billable_shipment, reference_data)
        service_quotes.append(quote)

    return service_quotes

def create_service_quote(billable_shipment: BillableShipmentResponse,
                         reference_data: ReferenceData) -> ServiceQuoteResponse:
    """Creates pricing service quote based on a billable shipment."""

    # get carrier and service details
    carrier_name = get_carrier_name(billable_shipment.carrier_service_code, reference_data.service_configuration)
    service_name = get_service_name(billable_shipment.carrier_service_code, reference_data.service_configuration)


    if billable_shipment.billable_weight > MAX_BILLABLE_WEIGHT:
        raise BadRequestError(
        "Billable weight exceeds maximum billable weight. "
        "No transportation charges are available."
    )

    # get transportation charge
    transportation_charge = get_transportation_charge(billable_shipment.carrier_service_code,
                                                      billable_shipment.zone,
                                                      billable_shipment.billable_weight,
                                                      reference_data.transportation_rates)
    fuel_eligible_amount = transportation_charge

    charges = []

    # apply residential surcharge
    if billable_shipment.residential_delivery:
        residential_surcharge = get_charge_rate(billable_shipment.carrier_service_code, "RES",
                                                          reference_data.charge_rates)
        charges.append(residential_surcharge)

        if residential_surcharge.fuel_applied:
            fuel_eligible_amount += residential_surcharge.amount

    # apply Saturday delivery fee
    if billable_shipment.saturday_delivery:
        saturday_surcharge = get_charge_rate(billable_shipment.carrier_service_code,"SAT",
                                             reference_data.charge_rates)
        charges.append(saturday_surcharge)
        if saturday_surcharge.fuel_applied:
            fuel_eligible_amount += saturday_surcharge.amount

    # apply Delivery Area Surcharge
    if billable_shipment.delivery_area_type is not None:

        if billable_shipment.delivery_area_type == DeliveryAreaType.COMMERCIAL:
            charge_code = "DASC"

        elif billable_shipment.delivery_area_type == DeliveryAreaType.RESIDENTIAL:
            charge_code = "DASR"

        elif billable_shipment.delivery_area_type == DeliveryAreaType.EXTENDED:
            charge_code = "EDAS"

        elif billable_shipment.delivery_area_type == DeliveryAreaType.REMOTE:
            charge_code = "REM"

        else:
            raise ValueError(
                f"Unsupported delivery area type: "
                f"{billable_shipment.delivery_area_type}"
            )

        delivery_charge = get_charge_rate(
            billable_shipment.carrier_service_code,
            charge_code,
            reference_data.charge_rates
        )

        charges.append(delivery_charge)

        if delivery_charge.fuel_applied:
            fuel_eligible_amount += delivery_charge.amount

    # apply signature service
    if billable_shipment.signature_required_type is not None:

        if billable_shipment.signature_required_type == SignatureType.REQUIRED:
            charge_code = "SIG"

        elif billable_shipment.signature_required_type == SignatureType.ADULT:
            charge_code = "ASIG"

        else:
            raise ValueError(
            f"Unsupported signature required type: "
            f"{billable_shipment.signature_required_type}"
            )

        signature_required_charge = get_charge_rate(billable_shipment.carrier_service_code,
                                                    charge_code,
                                                    reference_data.charge_rates)

        charges.append(signature_required_charge)

        if signature_required_charge.fuel_applied:
            fuel_eligible_amount += signature_required_charge.amount

    # apply large package surcharge
    if billable_shipment.large_package_type is not None:

        if billable_shipment.large_package_type == LargePackageType.LARGE_PACKAGE:
            charge_code = "LPS"

        elif billable_shipment.large_package_type == LargePackageType.OVER_MAX:
            charge_code = "MAX"

        else:
            raise ValueError(
                f"Unsupported large package type: "
                f"{billable_shipment.large_package_type}"
            )

        large_package_charge = get_charge_rate(billable_shipment.carrier_service_code,
                                               charge_code,
                                               reference_data.charge_rates)

        charges.append(large_package_charge)

        if large_package_charge.fuel_applied:
            fuel_eligible_amount += large_package_charge.amount

    # apply additional handling surcharge
    if (billable_shipment.additional_handling_type is not None
            and billable_shipment.large_package_type is None):

        if billable_shipment.additional_handling_type == AdditionalHandlingType.WEIGHT:
            charge_code = "ADW"

        elif billable_shipment.additional_handling_type == AdditionalHandlingType.DIMENSIONS:
            charge_code = "AHD"

        elif billable_shipment.additional_handling_type == AdditionalHandlingType.PACKAGING:
            charge_code = "AHP"

        else:
            raise ValueError(
                f"Unsupported additional handling type: "
                f"{billable_shipment.additional_handling_type}"
            )

        additional_handling_charge = get_charge_rate(billable_shipment.carrier_service_code,
                                        charge_code,
                                        reference_data.charge_rates)
        charges.append(additional_handling_charge)

        if additional_handling_charge.fuel_applied:
            fuel_eligible_amount += additional_handling_charge.amount

    # calculate insurance charge
    if billable_shipment.declared_value > 100:
        declared_value_rate = get_charge_rate(billable_shipment.carrier_service_code,
                                                "INS",
                                                reference_data.charge_rates)
        # calculate per 100 charge amount

        if billable_shipment.declared_value <= 300:
            declared_value_amount = declared_value_rate.amount

        else:
            factor = math.ceil(billable_shipment.declared_value / 100)
            declared_value_amount = round(declared_value_rate.amount * factor, 2)

        declared_value_charge = QuoteCharge(
            charge_code=declared_value_rate.charge_code,
            charge_description=declared_value_rate.charge_description,
            amount=declared_value_amount,
            fuel_applied=declared_value_rate.fuel_applied
        )

        charges.append(declared_value_charge)

        if declared_value_charge.fuel_applied:
            fuel_eligible_amount += declared_value_charge.amount

    # determine mode for fuel calculation
    transport_mode = get_transport_mode(billable_shipment.carrier_service_code,
                                        reference_data.service_configuration)

    if transport_mode == "ROAD":
        fuel_type = FuelType.DIESEL
    elif transport_mode == "AIR":
        fuel_type = FuelType.JET
    else:
        raise ValueError("transport_mode must be ROAD or AIR")

    # get fuel price to determine fuel percentage
    fuel_price = get_latest_fuel_price(fuel_type)

    if fuel_price is None:
        raise Exception(f"No fuel price found for {fuel_type.value}")

    fuel_pct = get_fuel_pct(billable_shipment.carrier_code,
                            transport_mode,
                            fuel_price,
                            reference_data.fuel_chart)

    fuel_charge = round(fuel_pct * fuel_eligible_amount, 2)

    # add all charges for total charge
    total_charge = transportation_charge + fuel_charge

    for charge in charges:
        total_charge += charge.amount

    total_charge = round(total_charge, 2)

    service_quote = ServiceQuoteResponse(
    quote_id=create_id(),
    shipment_id=billable_shipment.shipment_id,
    billable_shipment_id=billable_shipment.billable_shipment_id,
    carrier_service_code=billable_shipment.carrier_service_code,
    carrier_code=billable_shipment.carrier_code,
    carrier_name=carrier_name,
    service_code=billable_shipment.service_code,
    service_name=service_name,
    zone=billable_shipment.zone,
    billable_weight=billable_shipment.billable_weight,
    transportation_charge=transportation_charge,
    charges=charges,
    fuel_type=fuel_price.fuel_type,
    fuel_price=fuel_price.value,
    fuel_effective_date=fuel_price.effective_date,
    fuel_pct=fuel_pct,
    fuel_charge=fuel_charge,
    total_charge=total_charge,
    estimated_delivery=billable_shipment.estimated_delivery,
    created_at=get_timestamp()
)

    save_service_quote(service_quote.model_dump(mode="json"))

    return service_quote

import math
from datetime import datetime
import pandas as pd
import numpy as np

from src.billable_shipment.repository import save_billable_shipment, get_billable_shipments
from src.billable_shipment.schemas import BillableShipmentResponse
from src.common.enums import SignatureType, AdditionalHandlingType, LargePackageType, DeliveryAreaType
from src.common.exceptions import NotFoundError
from src.common.reference_data import get_reference_data
from src.common.utils import create_id, get_timestamp

def calculate_dimensional_weight(length: float,
                                 width: float,
                                 height: float,
                                 dim_factor: int) -> float:
    return length * width * height / dim_factor

def calculate_billable_weight(actual_weight: float,
                              dimensional_weight: float) -> int:
    return math.ceil(
        max(actual_weight, dimensional_weight))

def calculate_lane_mapping(orig_zip: str,
                           dest_zip: str,
                           zone_matrix: pd.DataFrame) -> pd.DataFrame:
    """find service/zone availability based on origin and destination zip"""

    orig_zip_num = int(orig_zip)
    dest_zip_num = int(dest_zip)

    service_lanes = zone_matrix[
        (zone_matrix["origin_zip_start_num"] <= orig_zip_num) &
        (zone_matrix["origin_zip_end_num"] >= orig_zip_num) &
        (zone_matrix["destination_zip_start_num"] <= dest_zip_num) &
        (zone_matrix["destination_zip_end_num"] >= dest_zip_num)]
    return service_lanes

def calculate_services_by_transit(requested_delivery: datetime,
                                   ship_date: datetime,
                                   service_lanes: pd.DataFrame) -> pd.DataFrame:
    """Return services whose transit commitment meets requested delivery."""

    available_lanes = service_lanes.dropna(
        subset=["transit_days", "transit_time"]).copy()

    estimated_deliveries = []

    for row in available_lanes.itertuples(index=False):
        delivery_date = np.busday_offset(
            ship_date.date(),
            int(row.transit_days),
            roll="forward")

        delivery_time = datetime.strptime(
            row.transit_time,
            "%H:%M").time()

        estimated_delivery = datetime.combine(
            pd.Timestamp(delivery_date).date(),
            delivery_time)

        estimated_deliveries.append(estimated_delivery)

    available_lanes["estimated_delivery"] = estimated_deliveries

    return available_lanes[
        available_lanes["estimated_delivery"] <= requested_delivery].copy()



def apply_residential_flag(residential_delivery: bool,
                           available_lanes: pd.DataFrame,
                           service_configuration:pd.DataFrame) -> pd.DataFrame:
    """Return services that provide residential or commercial delivery."""

    if residential_delivery:
        allowed_types = ["BOTH", "RESIDENTIAL"]
    else:
        allowed_types = ["BOTH", "COMMERCIAL"]

    eligible_services = service_configuration.loc[
        service_configuration["delivery_type"].isin(allowed_types),
        "carrier_service_code"]

    return available_lanes[
        available_lanes["carrier_service_code"].isin(eligible_services)].copy()

def apply_signature_service(signature_required: bool,
                            adult_signature_required: bool) -> SignatureType | None:
    """Return signature type if required, otherwise None."""

    if signature_required and adult_signature_required:
        raise ValueError(
            "Signature required and adult signature required "
            "cannot both be selected"
        )
    if signature_required:
        return SignatureType.REQUIRED
    if adult_signature_required:
        return SignatureType.ADULT
    return None

def apply_additional_handling(additional_handling_packaging: bool,
                              length: float,
                              width: float,
                              height: float,
                              actual_weight: float,
                              ah_weight_threshold: float,
                              ah_length_threshold: float,
                              ah_width_threshold: float,
                              ah_length_plus_girth_threshold: float) -> (AdditionalHandlingType | None):
    """Return additional handling type if applicable, otherwise None."""

    length_and_girth = length + (2 * height) + (2 * width)

    if actual_weight > ah_weight_threshold:
        return AdditionalHandlingType.WEIGHT

    if (length > ah_length_threshold or
        width > ah_width_threshold or
        length_and_girth > ah_length_plus_girth_threshold):
        return AdditionalHandlingType.DIMENSIONS

    if additional_handling_packaging:
        return AdditionalHandlingType.PACKAGING

    return None

def apply_large_package(length: float,
                        width: float,
                        height: float,
                        actual_weight: float,
                        large_package_length_threshold: float,
                        large_package_length_plus_girth_threshold: float,
                        large_package_weight: float,
                        max_weight: float,
                        max_length: float,
                        max_length_plus_girth: float) -> LargePackageType | None:
    """Return large package type if applicable, otherwise None."""

    length_and_girth = length + (2 * height) + (2 * width)

    if (actual_weight > max_weight or
            length > max_length or
            length_and_girth > max_length_plus_girth):
        return LargePackageType.OVER_MAX

    if (actual_weight > large_package_weight or
            length > large_package_length_threshold or
            length_and_girth > large_package_length_plus_girth_threshold):
        return LargePackageType.LARGE_PACKAGE

    return None

def apply_delivery_area(dest_zip: str,
                        residential_delivery: bool,
                        carrier_code: str,
                        das_zips: pd.DataFrame) -> DeliveryAreaType | None:
    """Return delivery area type if applicable, otherwise None."""

    match = das_zips.loc[(das_zips["zip_code"] == dest_zip) &
                            (das_zips["carrier_code"] == carrier_code), "das_type"]

    if match.empty:
        return None

    das_type = match.iloc[0]

    if das_type == "DAS" and residential_delivery:
        return DeliveryAreaType.RESIDENTIAL
    if das_type == "DAS":
        return DeliveryAreaType.COMMERCIAL
    if das_type == "EDAS":
        return DeliveryAreaType.EXTENDED
    if das_type == "REM":
        return DeliveryAreaType.REMOTE
    return None

def create_billable_shipments(raw_shipment) -> list[BillableShipmentResponse]:
    """Create billable shipments based on raw shipment data."""

    # load reference data
    reference_data = get_reference_data()

    # determine available lanes for orig/dest zips
    available_lanes = calculate_lane_mapping(raw_shipment.orig_zip,
                                             raw_shipment.dest_zip,
                                             reference_data.zone_matrix)
    print("After lane mapping:", len(available_lanes))

    # apply residential/commercial distinction to available lanes
    available_lanes = apply_residential_flag(raw_shipment.residential_delivery,
                                             available_lanes,
                                             reference_data.service_configuration)
    print("After residential filter:", len(available_lanes))

    # trim available lanes by transit
    available_lanes = calculate_services_by_transit(raw_shipment.requested_delivery,
                                             raw_shipment.ship_date,
                                             available_lanes)
    print("After transit filter:", len(available_lanes))

    # determine signature service
    signature_service = apply_signature_service(raw_shipment.signature_required,
                                                raw_shipment.adult_signature_required)

    billable_shipments = []

    for lane in available_lanes.itertuples(index=False):
        # create one billable shipment for the current eligible service

        match = reference_data.service_configuration.loc[
            reference_data.service_configuration["carrier_service_code"]
            == lane.carrier_service_code]

        if match.empty:
            raise ValueError( f"Service configuration not found for "
                              f"{lane.carrier_service_code}.")

        service_config = match.iloc[0]

        # determine dimensional weight
        dimensional_weight = calculate_dimensional_weight(raw_shipment.length,
                                                      raw_shipment.width,
                                                      raw_shipment.height,
                                                      service_config["dim_factor"])

        # determine billable weight
        billable_weight = calculate_billable_weight(raw_shipment.actual_weight,
                                                    dimensional_weight)

        # determine additional handling type
        additional_handling = apply_additional_handling(additional_handling_packaging=raw_shipment.additional_handling_packaging,
                                                        length=raw_shipment.length,
                                                        width=raw_shipment.width,
                                                        height=raw_shipment.height,
                                                        actual_weight=raw_shipment.actual_weight,
                                                        ah_weight_threshold=service_config["ah_weight_threshold"],
                                                        ah_length_plus_girth_threshold=service_config["ah_length_plus_girth_threshold"],
                                                        ah_length_threshold=service_config["ah_length_threshold"],
                                                        ah_width_threshold=service_config["ah_width_threshold"])

        # determine large package
        large_package = apply_large_package(length=raw_shipment.length,
                                            width=raw_shipment.width,
                                            height=raw_shipment.height,
                                            actual_weight=raw_shipment.actual_weight,
                                            large_package_length_threshold=service_config["large_package_length_threshold"],
                                            large_package_length_plus_girth_threshold=service_config["large_package_length_plus_girth_threshold"],
                                            large_package_weight=service_config["large_package_weight"],
                                            max_weight=service_config["max_weight"],
                                            max_length=service_config["max_length"],
                                            max_length_plus_girth=service_config["max_length_plus_girth"])

        # determine delivery area type
        delivery_area = apply_delivery_area(raw_shipment.dest_zip,
                                        raw_shipment.residential_delivery,
                                        service_config["carrier_code"],
                                        reference_data.das_zips
                                        )

        billable_shipment = {
            "billable_shipment_id": create_id(),
            "shipment_id": raw_shipment.shipment_id,
            "carrier_service_code": lane.carrier_service_code,
            "carrier_code": lane.carrier_code,
            "service_code": lane.service_code,
            "zone": int(lane.normalized_zone),
            "billable_weight": billable_weight,
            "residential_delivery": raw_shipment.residential_delivery,
            "signature_required_type": signature_service,
            "saturday_delivery": raw_shipment.saturday_delivery,
            "declared_value": raw_shipment.declared_value,
            "additional_handling_type": additional_handling,
            "large_package_type": large_package,
            "delivery_area_type": delivery_area,
            "reference": raw_shipment.reference,
            "estimated_delivery": lane.estimated_delivery,
            "created_at": get_timestamp(),
    }

        save_billable_shipment(billable_shipment)

        billable_shipments.append(
            BillableShipmentResponse(**billable_shipment)
        )
    return billable_shipments

def get_billable_shipments_by_shipment_id(shipment_id: str) -> list[BillableShipmentResponse]:
    billable_shipments = get_billable_shipments(shipment_id)
    if not billable_shipments:
        raise NotFoundError("billable shipments not found")
    return billable_shipments






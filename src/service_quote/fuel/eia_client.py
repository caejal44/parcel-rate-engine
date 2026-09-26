import os
import requests

from src.service_quote.fuel.schemas import FuelType, FuelPrice

EIA_API_KEY = os.environ["EIA_API_KEY"]

DIESEL_BASE_URL = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
JET_BASE_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

def get_latest_diesel_price() -> FuelPrice:
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": "EMD_EPD2D_PTE_NUS_DPG",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 1,
    }

    response = requests.get(DIESEL_BASE_URL, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    observations = data["response"]["data"]

    if not observations:
        raise ValueError("EIA returned no diesel price data.")

    latest = observations[0]

    return FuelPrice(
        fuel_type=FuelType.DIESEL,
        value=float(latest["value"]),
        effective_date=latest["period"],
        units=latest["units"],
    )

def get_latest_jet_fuel_price() -> FuelPrice:
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "daily",
        "data[0]": "value",
        "facets[series][]": "EER_EPJK_PF4_RGC_DPG",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 1,
    }

    response = requests.get(
        JET_BASE_URL,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()
    observations = data["response"]["data"]

    if not observations:
        raise ValueError("EIA returned no jet fuel price data.")

    latest = observations[0]

    return FuelPrice(
        fuel_type=FuelType.JET,
        value=float(latest["value"]),
        effective_date=latest["period"],
        units=latest["units"],
    )




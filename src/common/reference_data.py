import pathlib
import pandas as pd

from dataclasses import dataclass
from functools import lru_cache

from src.common.loaders import load_zone_matrix, load_service_configuration, load_das_zips, load_fuel_chart, \
    load_transportation_rates, load_charge_rates, load_orig_zips

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data_inputs"


@dataclass(frozen=True)
class ReferenceData:
    zone_matrix: pd.DataFrame
    service_configuration: pd.DataFrame
    das_zips: pd.DataFrame
    fuel_chart: pd.DataFrame
    transportation_rates: pd.DataFrame
    charge_rates: pd.DataFrame
    orig_zips: pd.DataFrame


@lru_cache(maxsize=1)
def get_reference_data() -> ReferenceData:
    return ReferenceData(
        zone_matrix=load_zone_matrix(
            DATA_PATH / "zone_matrix.csv"
        ),
        service_configuration=load_service_configuration(
            DATA_PATH / "service_configuration.csv"
        ),
        das_zips=load_das_zips(
            DATA_PATH / "das_zips.csv"
        ),
        fuel_chart=load_fuel_chart(
            DATA_PATH / "fuel_chart.csv"
        ),
        transportation_rates=load_transportation_rates(
            DATA_PATH / "transportation_rates.csv"
        ),
        charge_rates=load_charge_rates(
            DATA_PATH / "charge_rates.csv"
        ),
        orig_zips=load_orig_zips(
            DATA_PATH / "orig_zips.csv")

    )





from src.service_quote.fuel.eia_client import get_latest_diesel_price, get_latest_jet_fuel_price
from src.service_quote.fuel.repository import save_fuel_prices
from src.service_quote.fuel.schemas import FuelPrice


def refresh_fuel_prices() -> list[FuelPrice]:
    diesel = get_latest_diesel_price()
    jet = get_latest_jet_fuel_price()

    fuel_prices = [diesel, jet]

    save_fuel_prices(fuel_prices)

    return fuel_prices


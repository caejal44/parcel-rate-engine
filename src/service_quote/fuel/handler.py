from src.service_quote.fuel.service import refresh_fuel_prices


def lambda_handler(event, context):
    prices = refresh_fuel_prices()

    return {
        "prices": [
            price.model_dump(mode="json")
            for price in prices
        ]
    }
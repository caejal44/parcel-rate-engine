import boto3
from boto3.dynamodb.conditions import Key

from src.common.utils import prepare_for_dynamodb
from src.service_quote.fuel.schemas import FuelPrice, FuelType

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("fuel_table")


def save_fuel_prices(fuel_prices: list[FuelPrice]) -> None:
    for price in fuel_prices:
        item = price.model_dump(mode="json")
        item = prepare_for_dynamodb(item)

        table.put_item(Item=item)

def get_latest_fuel_price(fuel_type: FuelType) -> FuelPrice | None:
    response = table.query(
        KeyConditionExpression=Key("fuel_type").eq(fuel_type.value),
        ScanIndexForward=False,
        Limit=1
    )

    items = response["Items"]

    if not items:
        return None

    return FuelPrice(**items[0])
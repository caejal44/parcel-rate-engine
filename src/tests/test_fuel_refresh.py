import boto3

from src.service_quote.fuel.schemas import FuelType
from src.service_quote.fuel.service import refresh_fuel_prices


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("fuel_table")


def test_refresh_fuel_prices_saves_without_duplicates():
    first_refresh = refresh_fuel_prices()

    assert len(first_refresh) == 2
    assert {price.fuel_type for price in first_refresh} == {
        FuelType.DIESEL,
        FuelType.JET,
    }

    for price in first_refresh:
        response = table.get_item(
            Key={
                "fuel_type": price.fuel_type.value,
                "effective_date": price.effective_date.isoformat(),
            }
        )

        assert "Item" in response

        item = response["Item"]

        assert item["fuel_type"] == price.fuel_type.value
        assert item["effective_date"] == price.effective_date.isoformat()
        assert float(item["value"]) == price.value
        assert item["units"] == price.units

    second_refresh = refresh_fuel_prices()

    assert len(second_refresh) == 2

    for price in second_refresh:
        response = table.query(
            KeyConditionExpression=(
                "fuel_type = :fuel_type AND effective_date = :effective_date"
            ),
            ExpressionAttributeValues={
                ":fuel_type": price.fuel_type.value,
                ":effective_date": price.effective_date.isoformat(),
            },
        )

        assert response["Count"] == 1
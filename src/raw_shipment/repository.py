
import boto3

from src.common.utils import prepare_for_dynamodb

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('raw_shipments')

def save_raw_shipment(raw_shipment: dict) -> None:
    item = prepare_for_dynamodb(raw_shipment)
    table.put_item(Item=item)

def get_raw_shipment(shipment_id: str) -> dict | None:
    response = table.get_item(Key={"shipment_id": shipment_id})
    return response.get("Item")


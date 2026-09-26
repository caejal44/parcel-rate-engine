import boto3
from boto3.dynamodb.conditions import Key

from src.billable_shipment.schemas import BillableShipmentResponse
from src.common.utils import prepare_for_dynamodb

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('billable_shipments')

def save_billable_shipment(billable_shipment: dict) -> None:
    item = prepare_for_dynamodb(billable_shipment)
    table.put_item(Item=item)

def get_billable_shipments(shipment_id: str) -> list[BillableShipmentResponse]:

    response = table.query(IndexName="shipment_id",
        KeyConditionExpression=Key("shipment_id").eq(shipment_id))

    items = response.get("Items", [])

    return [
        BillableShipmentResponse(**item)
        for item in items
    ]
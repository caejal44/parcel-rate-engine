import boto3

from src.common.utils import prepare_for_dynamodb

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('service_quotes')

def save_service_quote(service_quote: dict) -> None:
    item = prepare_for_dynamodb(service_quote)
    table.put_item(Item=item)


import functools
import json
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal

from pydantic import ValidationError

from src.common.exceptions import BadRequestError, NotFoundError
from src.common.responses import error_response

def create_id() -> str:
    return str(uuid.uuid4())

def get_timestamp() -> datetime:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc)

def get_required_path_param(event, param_name: str) -> str:
    path_params = event.get("pathParameters") or {}
    param = path_params.get(param_name)
    if not param:
        raise BadRequestError( f"{param_name} is required")
    return param

def get_current_user_id(event) -> str:
    # temporary until Auth/Config
    return "user_456"

def error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except json.JSONDecodeError:
            return error_response(400,"invalid_json",
                                  "Request body contains invalid JSON")
        except ValidationError as error:
            return error_response(400, "validation_error", error.errors())

        except NotFoundError as error:
            return error_response(404, "not_found", str(error))

        except BadRequestError as error:
            return error_response(400, "bad_request", str(error))

        except Exception as error:
            return error_response(500, "internal_server_error", str(error))

    return wrapper

def prepare_for_dynamodb(value):
    """Convert application values to DynamoDB-compatible types."""
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: prepare_for_dynamodb(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            prepare_for_dynamodb(item)
            for item in value
        ]

    return value

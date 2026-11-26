"""Insert-only writes shared by gold loading and the protected synthetic seed.

A read followed by an unconditional write has a race. Ask DynamoDB to insert
only if absent; an existing, identical record is a skip, never an overwrite.
"""

import time
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from botocore.exceptions import BotoCoreError, ClientError

from .repository import RepositoryError


class WriteConflict(RepositoryError):
    """The destination key is already occupied by different data/provenance."""


def same_item(old: dict, new: dict) -> bool:
    """Compare flat records without confusing DynamoDB BOOL false with Number 0.

Python's decoded values consider False == Decimal(0). Preserve attribute types
while accepting equivalent numeric spellings such as 1 and 1.00.
"""
    if old.keys() != new.keys():
        return False
    for name, value in new.items():
        previous = old[name]
        if previous.keys() != value.keys():
            return False
        if "N" in value:
            try:
                if Decimal(previous["N"]) != Decimal(value["N"]):
                    return False
            except InvalidOperation:
                return False
        elif previous != value:
            return False
    return True


def conditional_put(client: Any, table: str, item: dict,
                    sleep: Callable[[float], None] = time.sleep) -> str:
    """Return written/skipped; bounded retries also resolve ambiguous successes."""
    for attempt in range(3):
        try:
            client.put_item(TableName=table, Item=item,
                ConditionExpression="attribute_not_exists(#pk)",
                ExpressionAttributeNames={"#pk": "PK"},
                ReturnValuesOnConditionCheckFailure="ALL_OLD")
            return "written"
        except ClientError as error:
            code = error.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                old = error.response.get("Item")
                # Some SDK/service responses omit ALL_OLD. Query the exact key
                # consistently, never Scan, and never infer a skip from absence.
                if old is None:
                    response = client.query(TableName=table, ConsistentRead=True,
                        KeyConditionExpression="#pk = :pk AND #sk = :sk",
                        ExpressionAttributeNames={"#pk": "PK", "#sk": "SK"},
                        ExpressionAttributeValues={":pk": item["PK"], ":sk": item["SK"]})
                    old = next(iter(response.get("Items", [])), None)
                if old is not None and same_item(old, item):
                    return "skipped"
                raise WriteConflict("Destination conflict; no existing record was overwritten.") from error
            if code not in {"ProvisionedThroughputExceededException", "ThrottlingException",
                            "RequestLimitExceeded", "InternalServerError"}:
                raise RepositoryError("Conditional write unavailable; inspect configuration and resume safely.") from error
        except BotoCoreError as error:
            # A transport failure might occur after AWS accepted the write.
            # Retrying the *conditional* insert cannot overwrite that result.
            if attempt == 2:
                raise RepositoryError("Conditional write transport retry limit; resume the same snapshot.") from error
        if attempt < 2:
            sleep(0.1 * 2 ** attempt)
    raise RepositoryError("Conditional write retry limit reached; some records may already exist.")

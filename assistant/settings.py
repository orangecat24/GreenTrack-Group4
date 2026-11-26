"""Standalone assistant settings with a credential-free default."""

import os
from pathlib import Path
from typing import Literal

from .athena import AthenaExecutor
from .bedrock import BedrockModel, Model, ScriptedModel
from .tools import FixtureExecutor, HourlyExecutor

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures/person3/gold_hourly.json"
HOUSEHOLDS = frozenset({"household-1"})
DataSource = Literal["synthetic_fixture", "athena"]


def configured_data_source() -> tuple[DataSource, HourlyExecutor]:
    """Choose the executor at startup, independently of the model mode."""
    mode = os.getenv("GREENTRACK_ASSISTANT_DATA_MODE", "fixture")
    if mode == "fixture":
        return "synthetic_fixture", FixtureExecutor(FIXTURE_PATH)
    if mode != "athena":
        raise ValueError("Choose fixture or athena for the assistant data mode.")

    workgroup = os.getenv("GREENTRACK_ASSISTANT_ATHENA_WORKGROUP", "").strip()
    if not workgroup:
        raise ValueError("Athena mode requires an approved workgroup with enforced result settings.")

    import boto3
    from botocore.config import Config

    # The dedicated workgroup supplies and enforces the result location and
    # encryption. Keep SDK retries off because AthenaExecutor owns that budget.
    client = boto3.client(
        "athena", region_name="eu-central-1",
        config=Config(connect_timeout=1, read_timeout=2, retries={"total_max_attempts": 1}),
    )
    return "athena", AthenaExecutor(client, workgroup=workgroup)


def configured_model() -> Model:
    """Construct cloud dependencies only when the model mode is explicitly enabled."""
    mode = os.getenv("GREENTRACK_ASSISTANT_MODEL_MODE", "scripted")
    if mode == "scripted":
        return ScriptedModel()
    if mode != "bedrock":
        raise ValueError("Choose scripted or bedrock for the assistant model mode.")

    model_id = os.environ["GREENTRACK_ASSISTANT_MODEL_ID"]
    guardrail_id = os.getenv("GREENTRACK_ASSISTANT_GUARDRAIL_ID")
    guardrail_version = os.getenv("GREENTRACK_ASSISTANT_GUARDRAIL_VERSION")
    if bool(guardrail_id) != bool(guardrail_version):
        raise ValueError("Supply both the guardrail ID and version.")
    guardrail = (guardrail_id, guardrail_version) if guardrail_id and guardrail_version else None

    import boto3
    from botocore.config import Config

    client = boto3.client(
        "bedrock-runtime",
        config=Config(connect_timeout=1, read_timeout=2, retries={"total_max_attempts": 1}),
    )
    return BedrockModel(client, model_id=model_id, guardrail=guardrail)

"""Standalone assistant settings with a credential-free default."""

import os
from pathlib import Path

from .bedrock import BedrockModel, Model, ScriptedModel

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures/person3/gold_hourly.json"
HOUSEHOLDS = frozenset({"household-1"})


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

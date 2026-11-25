"""Check the assistant archive and exercise its packaged scripted Lambda handler."""

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
from unittest.mock import patch
import zipfile

from build_assistant_zip import ARTIFACT, FIXTURE


def check_structure(archive: zipfile.ZipFile) -> None:
    """Check integrity, expected runtime entries and package boundaries."""
    entries = archive.namelist()
    names = set(entries)
    required = {
        "assistant/lambda_handler.py", "assistant/main.py", "assistant/service.py",
        "fastapi/__init__.py", "mangum/__init__.py", FIXTURE.as_posix(),
    }
    if len(names) != len(entries) or archive.testzip() is not None or not required <= names:
        raise RuntimeError("Unexpected assistant archive contents or invalid checksums.")
    if any(name.startswith(("api/", "app/", "assistant/tests/")) for name in names):
        raise RuntimeError("The archive includes files outside the assistant runtime.")
    if not any(name.startswith("pydantic_core/") and "x86_64" in name
               and name.endswith(".so") for name in names):
        raise RuntimeError("Missing Linux x86_64 pydantic-core library.")
    if json.loads(archive.read(FIXTURE.as_posix()))["is_synthetic"] is not True:
        raise RuntimeError("The archived fixture is not marked as synthetic.")


def check_handler(extracted: Path) -> None:
    """Invoke the extracted handler with an HTTP API v2 event and no AWS clients."""
    sys.path.insert(0, str(extracted))
    os.environ["GREENTRACK_ASSISTANT_MODEL_MODE"] = "scripted"
    with patch("boto3.client", side_effect=AssertionError("Unexpected AWS client")) as client:
        from assistant import lambda_handler
        import pydantic_core

        for module in (lambda_handler, pydantic_core):
            if not Path(module.__file__).resolve().is_relative_to(extracted):
                raise RuntimeError("Handler smoke used a host dependency.")
        event = {
            "version": "2.0", "routeKey": "POST /chat", "rawPath": "/chat",
            "rawQueryString": "", "headers": {"content-type": "application/json"},
            "requestContext": {
                "stage": "$default",
                "http": {"method": "POST", "path": "/chat", "sourceIp": "127.0.0.1"},
            },
            "body": json.dumps({
                "household_id": "household-1",
                "start": "2009-06-01T00:00:00Z",
                "end": "2009-06-02T00:00:00Z",
                "message": "How much energy did we use on June 1, 2009?",
            }),
            "isBase64Encoded": False,
        }
        response = lambda_handler.handler(event, None)
        client.assert_not_called()
    body = json.loads(response["body"])
    if (
        response["statusCode"] != 200
        or body["status"] != "ok"
        or "9.75 kWh across 210 of 1,440 minutes" not in body["answer"]
        or body["coverage"]["measured_minutes"] != 210
        or body["coverage"]["expected_minutes"] != 1440
        or body["provenance"]["source"] != "synthetic_fixture"
        or body["is_demo"] is not True
        or body["assistant_connected"] is not False
    ):
        raise RuntimeError("The packaged reply did not match the synthetic milestone.")


def main() -> None:
    """Check structure everywhere and execute only on the Linux target."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure-only", action="store_true",
                        help="Inspect file contents without importing Linux extensions.")
    options = parser.parse_args()
    with zipfile.ZipFile(ARTIFACT) as archive:
        check_structure(archive)
        print("Assistant ZIP structure and fixture passed.")
        if options.structure_only:
            return
        if (sys.platform != "linux" or sys.version_info[:2] != (3, 14)
                or platform.machine() != "x86_64"):
            raise SystemExit("Handler execution requires Linux x86_64 CPython 3.14.")
        with tempfile.TemporaryDirectory(prefix="greentrack-assistant-zip-") as temporary:
            extracted = Path(temporary).resolve()
            archive.extractall(extracted)
            check_handler(extracted)
    print("Packaged assistant handler passed the scripted Lambda event check.")


if __name__ == "__main__":
    main()

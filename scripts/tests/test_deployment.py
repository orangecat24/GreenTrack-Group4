"""Offline regressions for deployment boundaries and publication ordering."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deployment


@pytest.fixture(autouse=True)
def isolated_ci(monkeypatch, tmp_path):
    """Use temporary outputs and fail if any test tries a real command."""
    def forbidden(*args, **kwargs):
        """No Terraform/AWS/network process belongs in a local unit test."""
        raise AssertionError("Unexpected real subprocess")

    monkeypatch.setattr(deployment.subprocess, "run", forbidden)
    monkeypatch.setattr(deployment, "ROOT", tmp_path)
    monkeypatch.setattr(deployment, "BUILD", tmp_path / "build")
    for key, value in {
        "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "orangecat24/GreenTrack-Group4",
        "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/main", "DEPLOY_ENABLED": "true",
        "GITHUB_OUTPUT": str(tmp_path / "job-output"),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("TRUSTED_PR_PLAN", raising=False)


def application():
    """Public Terraform output example, with no state or credentials."""
    return {"api_base_url": "https://abc123.execute-api.eu-central-1.amazonaws.com",
            "website_url": "https://demo123.cloudfront.net",
            "frontend_bucket_name": "g4-greentrack-dev-web-886565871385",
            "cloudfront_distribution_id": "E1234567890"}


@pytest.mark.parametrize("key,value", [
    ("GITHUB_ACTIONS", "false"), ("DEPLOY_ENABLED", "false"),
    ("GITHUB_REF", "refs/heads/feature"), ("GITHUB_EVENT_NAME", "pull_request"),
    ("GITHUB_REPOSITORY", "another/repository"),
])
def test_writes_rejected_before_any_command(monkeypatch, key, value):
    """Neither a local invocation, disabled setup nor a PR can apply/upload."""
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        deployment.terraform_operation("apply")
    with pytest.raises(ValueError):
        deployment.publish()


def test_wrong_account_rejected_before_terraform(monkeypatch):
    """A working AWS session in the wrong account must not reach the backend."""
    monkeypatch.setattr(deployment, "run", lambda command: "111111111111")
    with pytest.raises(ValueError, match="account"):
        deployment.terraform_operation("init")


def test_main_apply_uses_exact_saved_plan(monkeypatch):
    """No second plan or auto-approved unplanned apply can replace the saved one."""
    commands = []

    def record(command):
        """Pretend Terraform produced its binary at the requested path."""
        commands.append(command)
        if command[0] == "aws":
            return deployment.ACCOUNT
        for argument in command:
            if argument.startswith("-out="):
                Path(argument[5:]).write_bytes(b"fake plan")
        return ""

    monkeypatch.setattr(deployment, "run", record)
    deployment.terraform_operation("plan")
    deployment.terraform_operation("apply")
    terraform = [cmd for cmd in commands if cmd[0] == "terraform"]
    saved = next(arg[5:] for arg in terraform[0] if arg.startswith("-out="))
    assert terraform[1][-1] == saved
    assert "-lock-timeout=5m" in terraform[0] and "-lock-timeout=5m" in terraform[1]
    assert all("-target" not in arg for cmd in terraform for arg in cmd)


def test_speculative_plan_never_locks_or_applies(monkeypatch):
    """The read-only PR role needs no S3 lock write and cannot promote its plan."""
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("TRUSTED_PR_PLAN", "true")
    commands = []

    def record(command):
        """Capture argv only; no executable is launched."""
        commands.append(command)
        return deployment.ACCOUNT if command[0] == "aws" else ""

    monkeypatch.setattr(deployment, "run", record)
    deployment.terraform_operation("plan", pr=True)
    assert "-lock=false" in commands[-1]
    with pytest.raises(ValueError):
        deployment.terraform_operation("apply", pr=True)


@pytest.mark.parametrize("key,bad", [
    ("api_base_url", "https://wrong.example.com/api"),
    ("website_url", "http://localhost:5173"),
    ("frontend_bucket_name", "another-groups-bucket"),
    ("cloudfront_distribution_id", "E1234567890\nINJECTED=value"),
])
def test_outputs_cannot_redirect_publication_or_inject_job_values(key, bad):
    """Only exact account destinations and single-line HTTPS prefixes are valid."""
    with pytest.raises(ValueError, match=key):
        deployment.validated_outputs({**application(), key: bad})


def test_raw_command_values_are_not_exposed(monkeypatch):
    """An AWS/Terraform failure must not print captured secrets or plan values."""
    monkeypatch.setattr(deployment.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args, 1, "private-state-value", "AccessDenied private-token"))
    with pytest.raises(RuntimeError) as error:
        deployment.run(["terraform", "plan"])
    assert "AccessDenied" in str(error.value)
    assert "private" not in str(error.value)


@pytest.mark.parametrize("unchanged", [False, True])
def test_publish_orders_assets_and_invalidates_only_changed_html(monkeypatch, unchanged):
    """Preserve old asset hashes, publish HTML last and avoid needless invalidations."""
    dist = deployment.ROOT / "web/dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "assets/index-abcdefgh.js").write_text("script", encoding="utf-8")
    (dist / "assets/index-abcdefgh.css").write_text("styles", encoding="utf-8")
    (dist / "index.html").write_bytes(b"<html>demo</html>")
    deployment.BUILD.mkdir()
    (deployment.BUILD / "application.json").write_text(json.dumps(application()), encoding="utf-8")
    etag = hashlib.md5((dist / "index.html").read_bytes(), usedforsecurity=False).hexdigest()
    monkeypatch.setattr(deployment.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args, 0 if unchanged else 1,
                                                    f'"{etag}"' if unchanged else "", "" if unchanged else "(404) Not Found"))
    commands = []

    def record(command):
        """Return only the tiny responses needed by this simulated publication."""
        commands.append(command)
        if command[1] == "sts":
            return deployment.ACCOUNT
        return json.dumps({"Invalidation": {"Id": "fake-id"}})

    monkeypatch.setattr(deployment, "run", record)
    deployment.publish()
    copies = [cmd for cmd in commands if cmd[1:3] == ["s3", "cp"]]
    assert all("--delete" not in cmd for cmd in commands)
    assert all("public,max-age=31536000,immutable" in cmd for cmd in copies[:2])
    assert any("application/javascript" in cmd for cmd in copies)
    invalidations = [cmd for cmd in commands if "create-invalidation" in cmd]
    if unchanged:
        assert len(copies) == 2 and not invalidations
    else:
        assert copies[-1][4].endswith("/index.html")
        assert "no-cache,max-age=0,must-revalidate" in copies[-1]
        assert invalidations[0][-5:-3] == ["/", "/index.html"]

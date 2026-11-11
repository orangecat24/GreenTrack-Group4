"""Small CI-only deployment operations; no work runs when this module is imported.

Terraform owns resources. This helper selects only the existing dev root, keeps
plans/state out of logs, validates public outputs, and publishes built files.
Unit tests replace command execution; do not invoke live subcommands locally.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "infra/environments/dev"
BUILD = ROOT / "build"
ACCOUNT = "886565871385"
REGION = "eu-central-1"
DEPLOY_ROLE = f"arn:aws:iam::{ACCOUNT}:role/g4-greentrack-github-deploy"


def require_context(*, write: bool) -> None:
    """Prevent accidental local execution and writes from PR jobs."""
    if os.getenv("GITHUB_ACTIONS") != "true":
        raise ValueError("These live operations run only in the configured GitHub jobs.")
    if os.getenv("GITHUB_REPOSITORY") != "orangecat24/GreenTrack-Group4":
        raise ValueError("Unexpected repository.")
    main = os.getenv("GITHUB_EVENT_NAME") == "push" and os.getenv("GITHUB_REF") == "refs/heads/main"
    if write or main:
        if not main or os.getenv("DEPLOY_ENABLED") != "true":
            raise ValueError("Deployment requires an explicitly enabled main push.")
    elif os.getenv("GITHUB_EVENT_NAME") != "pull_request" or os.getenv("TRUSTED_PR_PLAN") != "true":
        raise ValueError("PR planning requires the explicitly configured trusted-PR job.")


def run(command: list[str]) -> str:
    """Capture command output: never echo state, plan values, bodies or tokens."""
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode:
        # Only fixed diagnostic categories enter shared logs. Raw output is not
        # retained/uploaded; owners reproduce detailed failures locally.
        category = next((name for name in (
            "AccessDenied", "InvalidIdentityToken", "ExpiredToken", "AlreadyExists",
            "NoSuchEntity", "LimitExceeded", "ResourceConflict", "Backend initialization required",
        ) if name in result.stderr + result.stdout), "command failure")
        raise RuntimeError(f"{command[0]} failed ({category}); see deployment troubleshooting.")
    return result.stdout


def verify_account() -> None:
    """Check the real credentials before backend access or resource writes."""
    account = run(["aws", "sts", "get-caller-identity", "--query", "Account",
                   "--output", "text", "--region", REGION, "--no-cli-pager"]).strip()
    if account != ACCOUNT:
        raise ValueError("AWS identity does not match the project's account.")


def validated_outputs(value: dict) -> dict[str, str]:
    """Allow only this project's public destinations into commands/job outputs."""
    patterns = {
        "api_base_url": r"https://[a-z0-9]+\.execute-api\.eu-central-1\.amazonaws\.com",
        "website_url": r"https://[a-z0-9]+\.cloudfront\.net",
        "frontend_bucket_name": r"g4-greentrack-dev-web-886565871385",
        "cloudfront_distribution_id": r"[A-Z0-9]{8,32}",
    }
    selected = {}
    for key, pattern in patterns.items():
        item = value.get(key)
        if not isinstance(item, str) or not re.fullmatch(pattern, item):
            raise ValueError(f"Unexpected application output: {key}")
        selected[key] = item
    return selected


def terraform_operation(operation: str, *, pr: bool = False) -> None:
    """Use one saved plan in one runner; never apply a PR's speculative plan."""
    require_context(write=operation in ("apply", "outputs"))
    is_pr = os.getenv("GITHUB_EVENT_NAME") == "pull_request"
    if pr != is_pr:
        raise ValueError("The plan mode must match the GitHub event.")
    verify_account()
    BUILD.mkdir(exist_ok=True)
    prefix = ["terraform", f"-chdir={DEV}"]
    plan = BUILD / ("pr.tfplan" if pr else "application.tfplan")
    if operation == "init":
        run(prefix + ["init", "-reconfigure", "-input=false", "-lockfile=readonly"])
    elif operation == "plan":
        # No lock write in the read-only PR session. This is speculative and is
        # never promoted to deployment. Main uses the backend's native S3 lock.
        locking = ["-lock=false"] if pr else ["-lock-timeout=5m"]
        run(prefix + ["plan", "-input=false", "-no-color", "-var=app_data_mode=mock",
                      *locking, f"-out={plan}"])
    elif operation == "apply":
        if not plan.is_file():
            raise ValueError("The same runner's saved main plan is missing.")
        run(prefix + ["apply", "-input=false", "-no-color", "-lock-timeout=5m", str(plan)])
    else:
        # Ask for ONLY the public application output, not all state or outputs.
        values = validated_outputs(json.loads(run(prefix + ["output", "-json", "application"])))
        (BUILD / "application.json").write_text(json.dumps(values), encoding="utf-8")
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            for key, value in values.items():
                output.write(f"{key}={value}\n")
    print(f"Terraform {operation} succeeded ({'speculative PR' if pr else 'main deployment'}).")


def upload_plan(dist: Path) -> list[tuple[Path, str, str]]:
    """Classify assets before uploading anything; index.html must be last."""
    mime_types = {".js": "application/javascript", ".css": "text/css", ".svg": "image/svg+xml",
                  ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2"}
    files = []
    for source in sorted(dist.rglob("*")):
        if not source.is_file():
            continue
        if source.is_symlink() or not source.resolve().is_relative_to(dist.resolve()):
            raise ValueError("Build output must not link to files outside dist.")
        key = source.relative_to(dist).as_posix()
        if key == "index.html":
            continue
        if source.suffix not in mime_types:
            raise ValueError(f"Add an explicit MIME/cache rule before publishing {key}.")
        hashed = key.startswith("assets/") and re.search(r"-[A-Za-z0-9_-]{8,}\.", source.name)
        if key.startswith("assets/") and not hashed:
            raise ValueError("Assets need content hashes before using immutable cache headers.")
        cache = "public,max-age=31536000,immutable" if hashed else "public,max-age=60"
        files.append((source, mime_types[source.suffix], cache))
    index = dist / "index.html"
    if not index.is_file() or index.is_symlink():
        raise ValueError("Frontend index.html is missing or is a symlink.")
    return files + [(index, "text/html", "no-cache,max-age=0,must-revalidate")]


def publish() -> None:
    """Upload assets before HTML, retain old hashes, invalidate changed HTML only."""
    require_context(write=True)
    verify_account()
    values = validated_outputs(json.loads((BUILD / "application.json").read_text(encoding="utf-8")))
    dist = ROOT / "web/dist"
    files = upload_plan(dist)
    bucket = values["frontend_bucket_name"]
    # ETag is MD5 for our small, single-part AES256 S3 HTML object. A different
    # ETag simply causes a safe re-upload/invalidation; it cannot hide a change.
    result = subprocess.run([
        "aws", "s3api", "head-object", "--bucket", bucket, "--key", "index.html",
        "--expected-bucket-owner", ACCOUNT, "--query", "ETag", "--output", "text",
        "--region", REGION, "--no-cli-pager",
    ], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode and not any(code in result.stderr for code in ("(404)", "NoSuchKey", "Not Found")):
        raise RuntimeError("Cannot check existing frontend HTML; verify S3 permissions.")
    old_hash = result.stdout.strip().strip('"') if not result.returncode else ""
    new_hash = hashlib.md5((dist / "index.html").read_bytes(), usedforsecurity=False).hexdigest()
    changed = old_hash != new_hash
    for source, mime, cache in files:
        key = source.relative_to(dist).as_posix()
        if key == "index.html" and not changed:
            continue
        run(["aws", "s3", "cp", str(source), f"s3://{bucket}/{key}", "--content-type", mime,
             "--cache-control", cache, "--only-show-errors", "--region", REGION, "--no-cli-pager"])
    if changed:
        response = json.loads(run([
            "aws", "cloudfront", "create-invalidation", "--distribution-id",
            values["cloudfront_distribution_id"], "--paths", "/", "/index.html", "--output", "json", "--no-cli-pager",
        ]))
        run(["aws", "cloudfront", "wait", "invalidation-completed", "--distribution-id",
             values["cloudfront_distribution_id"], "--id", response["Invalidation"]["Id"], "--no-cli-pager"])
    print("Frontend published; old hashed assets retained; HTML invalidated only if changed.")


def main() -> None:
    """Expose explicit CI steps so a failure identifies its phase in Actions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["init", "plan", "apply", "outputs", "publish"])
    parser.add_argument("--pr", action="store_true", help="Read-only, non-locking speculative plan; never apply.")
    args = parser.parse_args()
    try:
        if args.operation == "publish":
            if args.pr:
                raise ValueError("PR jobs cannot publish.")
            publish()
        else:
            terraform_operation(args.operation, pr=args.pr)
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()

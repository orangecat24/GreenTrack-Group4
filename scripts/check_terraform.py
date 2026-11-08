"""Run the same credential-free Terraform configuration checks locally and in CI.

No Terraform files means an explicit skip. Once configurations exist, require
reviewed root paths and a pinned CLI, rather than guessing that every child
module can be initialized as an independent deployment.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def discover() -> tuple[list[Path], list[Path], str]:
    """Find versioned/local source files while excluding ignored generated trees."""
    tracked = subprocess.check_output([
        "git", "ls-files", "-z", "--cached", "--others", "--exclude-standard",
        "--", "*.tf", "*.tf.json",
    ], cwd=ROOT).decode("utf-8").split("\0")
    files = [ROOT / name for name in tracked if name]
    if not files:
        print("SKIP: no Terraform configurations exist in this checkout.")
        return [], [], ""
    if any(not path.resolve().is_relative_to(ROOT) for path in files):
        raise ValueError("Terraform sources must stay within the repository.")
    roots = []
    for line in (ROOT / ".github/terraform-roots.txt").read_text(encoding="utf-8").splitlines():
        name = line.split("#", 1)[0].strip()
        if not name:
            continue
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not any(file.parent.resolve() == path for file in files):
            raise ValueError(f"Register an existing repository Terraform root, not an external/empty directory: {name}")
        if path not in roots:
            roots.append(path)
    if not roots:
        raise ValueError("Terraform files found: register deployable root directories in .github/terraform-roots.txt.")
    version_path = ROOT / ".terraform-version"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.exists() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Add an exact Terraform CLI version (X.Y.Z) in .terraform-version.")
    for path in roots:
        if not (path / ".terraform.lock.hcl").is_file():
            raise ValueError(f"Commit the provider lock file for {path.relative_to(ROOT)} before running CI.")
    return sorted({file.parent.resolve() for file in files}), roots, version


def run(command: list[str]) -> None:
    """Use argument lists so spaces in Windows checkout paths remain safe."""
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    """Discover for Actions setup, or run fmt/init/validate with an installed CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true", help="Report configuration readiness without invoking Terraform.")
    args = parser.parse_args()
    try:
        directories, roots, version = discover()
        if args.discover:
            # GitHub supplies this file path. Only validated booleans/version
            # digits enter outputs; no repository text is injected into shell code.
            output = os.getenv("GITHUB_OUTPUT")
            if output:
                with open(output, "a", encoding="utf-8") as handle:
                    handle.write(f"has_terraform={'true' if roots else 'false'}\nterraform_version={version}\n")
            for path in roots:
                print(f"Terraform root: {path.relative_to(ROOT)} (CLI {version})")
            return 0
        if not roots:
            return 0
        executable = shutil.which("terraform")
        if not executable:
            raise ValueError(f"Install Terraform {version} before running these checks.")
        installed = json.loads(subprocess.check_output([executable, "version", "-json"], cwd=ROOT))
        if installed["terraform_version"] != version:
            raise ValueError(f"Use Terraform {version}, as pinned in .terraform-version.")
        # Format every source directory, including shared modules outside roots.
        # Do not recurse into node_modules, .venv, or downloaded .terraform trees.
        for path in directories:
            run([executable, f"-chdir={path}", "fmt", "-check", "-diff"])
        for path in roots:
            run([executable, f"-chdir={path}", "init", "-backend=false", "-input=false", "-lockfile=readonly"])
            run([executable, f"-chdir={path}", "validate", "-no-color"])
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Terraform checks failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

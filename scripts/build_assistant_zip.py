"""Build the independent Linux CPython 3.14 x86_64 assistant Lambda ZIP."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

from build_lambda import BUILD, ROOT, wheel_files, write_archive

ARTIFACT = BUILD / "greentrack-assistant.zip"
FIXTURE = Path("fixtures/person3/gold_hourly.json")


def main() -> None:
    """Resolve pinned Linux wheels and package the assistant and synthetic rows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, help="Resolve wheels from this local directory offline.")
    options = parser.parse_args()
    if sys.version_info[:2] != (3, 14):
        raise SystemExit("Run this script with Python 3.14.")
    BUILD.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="assistant-wheels-", dir=BUILD) as temporary:
        wheels = Path(temporary)
        source = []
        if options.wheel_dir is not None:
            source = ["--no-index", "--find-links", str(options.wheel_dir.resolve(strict=True))]
        subprocess.run([
            sys.executable, "-m", "pip", "--isolated", "download",
            "--disable-pip-version-check", "--only-binary=:all:", "--no-deps",
            "--platform", "manylinux_2_28_x86_64", "--platform", "manylinux2014_x86_64",
            "--platform", "manylinux_2_17_x86_64", "--implementation", "cp",
            "--python-version", "3.14", "--abi", "cp314", "--abi", "abi3", "--abi", "none",
            "--dest", str(wheels), "-r", str(ROOT / "assistant/requirements.txt"), *source,
        ], cwd=ROOT, check=True)
        files = wheel_files(wheels)
        for path in [*sorted((ROOT / "assistant").glob("*.py")), ROOT / FIXTURE]:
            name = path.relative_to(ROOT).as_posix()
            files[name] = path.read_text(encoding="utf-8").encode("utf-8")
        write_archive(ARTIFACT, files)
    print(f"Built {ARTIFACT.relative_to(ROOT)} ({ARTIFACT.stat().st_size:,} bytes)")
    print(f"SHA256 {hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()

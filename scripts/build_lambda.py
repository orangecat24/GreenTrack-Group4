"""Build a deterministic Linux/CPython 3.14 x86_64 Lambda ZIP, even on Windows.

Only pinned wheels are downloaded. We never copy the host .venv or compile native
code. Wheel availability is a hard requirement: a missing Linux wheel fails the
build instead of accidentally packaging a Windows binary or changing Python.
"""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
ARTIFACT = BUILD / "greentrack-api.zip"


def package_files(wheels: Path) -> dict[str, bytes]:
    """Unpack runtime wheels and source; reject unsafe paths or host binaries."""
    files: dict[str, bytes] = {}
    for wheel in sorted(wheels.glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                name = entry.filename
                if name.startswith("/") or ".." in name.split("/") or "\\" in name:
                    raise ValueError("A wheel contains an unsafe archive path.")
                # Wheels may contain optional CLI helpers (jmespath's jp.py).
                # Lambda needs library relocations, not scripts installed in bin/.
                parts = name.split("/")
                if parts[0].endswith(".data"):
                    if parts[1] == "scripts":
                        continue
                    if parts[1] not in ("purelib", "platlib"):
                        raise ValueError(f"Unsupported wheel data relocation: {name}")
                    name = "/".join(parts[2:])
                if name.endswith((".pyd", ".dll", ".dylib")):
                    raise ValueError(f"Non-Linux native library: {name}")
                content = archive.read(entry)
                if name.endswith(".so"):
                    # ELF64, little endian, machine 62 = AMD64 (not ARM64).
                    if content[:6] != b"\x7fELF\x02\x01" or content[18:20] != b"\x3e\x00":
                        raise ValueError(f"Not a Linux x86_64 library: {name}")
                if name in files:
                    raise ValueError(f"Overlapping wheel files: {name}")
                files[name] = content
    # Copy only application Python source. No seed loader, .env, tests or caches.
    for source in sorted((ROOT / "api/app").rglob("*.py")):
        # Git may use CRLF in a Windows checkout and LF in CI. Normalize source
        # newlines so that the ZIP hash does not depend on that checkout setting.
        files[source.relative_to(ROOT / "api").as_posix()] = source.read_text(encoding="utf-8").encode("utf-8")
    if not any(name.startswith("pydantic_core/") and name.endswith(".so") for name in files):
        raise ValueError("The Linux pydantic-core extension is missing.")
    return files


def main() -> None:
    """Download explicitly targeted wheels and write a stable, sorted ZIP."""
    if sys.version_info[:2] != (3, 14):
        raise SystemExit("Run this script with Python 3.14.")
    BUILD.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lambda-wheels-", dir=BUILD) as temporary:
        wheels = Path(temporary)
        subprocess.run([
            sys.executable, "-m", "pip", "--isolated", "download",
            "--disable-pip-version-check", "--only-binary=:all:", "--no-deps",
            "--platform", "manylinux_2_28_x86_64",
            "--platform", "manylinux2014_x86_64",
            "--platform", "manylinux_2_17_x86_64",
            "--implementation", "cp", "--python-version", "3.14",
            "--abi", "cp314", "--abi", "abi3", "--abi", "none",
            "--dest", str(wheels), "-r", str(ROOT / "api/requirements.txt"),
        ], cwd=ROOT, check=True)
        files = package_files(wheels)
        with zipfile.ZipFile(ARTIFACT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in sorted(files.items()):
                # Fixed timestamps, permissions and order remove host differences.
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, content, compresslevel=9)
    print(f"Built {ARTIFACT.relative_to(ROOT)} ({ARTIFACT.stat().st_size:,} bytes)")
    print(f"SHA256 {hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()

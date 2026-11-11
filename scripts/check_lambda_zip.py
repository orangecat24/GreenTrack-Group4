"""On Linux Python 3.14, import and invoke the actual ZIP without AWS or credentials."""

from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Reuse the offline Lambda contract tests against the extracted artifact."""
    if sys.platform != "linux" or sys.version_info[:2] != (3, 14):
        raise SystemExit("ZIP execution requires Linux CPython 3.14; Windows can build but not import Linux .so files.")
    with tempfile.TemporaryDirectory(prefix="greentrack-zip-") as temporary:
        with zipfile.ZipFile(ROOT / "build/greentrack-api.zip") as archive:
            archive.extractall(temporary)
        sys.path.insert(0, temporary)
        # Test source is reused, but app/ and its runtime dependencies must come
        # from the artifact. pytest itself remains in the CI development venv.
        import app
        import pydantic_core

        for module in (app, pydantic_core):
            if not Path(module.__file__).resolve().is_relative_to(Path(temporary)):
                raise RuntimeError("ZIP check imported a host dependency.")
        import pytest

        result = pytest.main([
            "-c", str(ROOT / "api/pytest.ini"),
            str(ROOT / "api/tests/test_lambda.py"), "-q",
        ])
        if result:
            raise SystemExit(result)
        print("Actual Linux ZIP passed the offline Lambda event tests.")


if __name__ == "__main__":
    main()

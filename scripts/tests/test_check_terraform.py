"""Offline check isolation after a developer has initialized the real backend."""

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_terraform


def test_checks_do_not_reuse_live_backend_metadata(monkeypatch, tmp_path):
    """Init/validate share isolated data, never the user's cached S3 backend."""
    root = tmp_path / "infra/environments/dev"
    root.mkdir(parents=True)
    monkeypatch.setattr(check_terraform, "ROOT", tmp_path)
    monkeypatch.setattr(check_terraform, "discover", lambda: ([root], [root], "1.17.0"))
    monkeypatch.setattr(check_terraform.shutil, "which", lambda name: "terraform")
    monkeypatch.setattr(check_terraform.subprocess, "check_output", lambda *args, **kwargs:
                        json.dumps({"terraform_version": "1.17.0"}).encode())
    monkeypatch.setattr(sys, "argv", ["check_terraform.py"])
    monkeypatch.setenv("TF_DATA_DIR", str(tmp_path / "existing-live-data"))
    calls = []
    monkeypatch.setattr(check_terraform, "run", lambda command, **kwargs: calls.append((command, kwargs)))
    assert check_terraform.main() == 0
    init, validate = calls[-2:]
    assert "-backend=false" in init[0]
    assert init[1]["env"]["TF_DATA_DIR"] == validate[1]["env"]["TF_DATA_DIR"]
    assert init[1]["env"]["TF_DATA_DIR"] != os.environ["TF_DATA_DIR"]
    assert Path(init[1]["env"]["TF_DATA_DIR"]).is_relative_to(tmp_path / "build/terraform-checks")
    assert Path(init[1]["env"]["TF_DATA_DIR"]).is_dir()

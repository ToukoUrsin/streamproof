from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from streamproof import app as module

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "DATA", tmp_path)
    monkeypatch.setattr(module, "DB", tmp_path / "observations.sqlite3")
    monkeypatch.delenv("STREAMPROOF_TOKEN", raising=False)
    (tmp_path / "images").mkdir()
    with TestClient(module.app) as client:
        yield client


@pytest.fixture
def samples():
    return {sample["id"]: sample for sample in module.samples_manifest()}

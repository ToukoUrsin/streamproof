"""Exercise actual HTTP, image decoder, OpenCV, persistence and evidence export."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from streamproof.integrity import verify_export

ROOT = Path(__file__).resolve().parent.parent


def submit(client, samples, ident, **metadata):
    sample = samples[ident]
    return client.post("/api/analyze", files={"image": (sample["file"], (ROOT / "samples" / sample["file"]).read_bytes(), "image/png")}, data={"roi": json.dumps(sample["roi"]), "metadata": json.dumps({"site": sample["site"], "roi_confirmed": True, "sample_id": ident, **metadata})})


def test_full_evidence_loop(client, samples):
    baseline = submit(client, samples, "control-baseline").json()
    assert baseline["policy"]["state"] == "baseline"
    assert baseline["opencv"].startswith("5.")
    response = submit(client, samples, "control-change", reference_id=baseline["id"], latitude=51.752, longitude=-0.343)
    assert response.status_code == 200
    changed = response.json()
    assert changed["policy"]["state"] == "change"
    assert .60 < changed["comparison"]["changed_fraction"] < .75
    assert changed["comparison"]["matches"] > 100
    assert changed["provenance"]["kind"] == "synthetic_fixture"
    assert not changed["provenance"]["field_validation"]
    original = client.get(f"/api/observations/{changed['id']}/image").content
    overlay = client.get(f"/api/observations/{changed['id']}/image?overlay=true").content
    assert original.startswith(b"\x89PNG") and overlay.startswith(b"\x89PNG")
    assert hashlib.sha256(original).hexdigest() == changed["normalized_sha256"]
    assert overlay != original
    assessment = {"reviewer": "Integration test", "assessment": "more_evidence", "note": "Controlled change only; collect another view before interpretation."}
    reviewed = client.post(f"/api/observations/{changed['id']}/review", json=assessment)
    assert reviewed.status_code == 200
    assert reviewed.json()["review"]["water_safety"] == "not_assessed"
    document = client.get("/api/export").json()
    result = verify_export(document)
    assert result["valid"], result["failures"]
    assert result["events"] == 3
    geo = client.get("/api/export?format=geojson").json()
    located = next(f for f in geo["features"] if f["id"] == changed["id"])
    assert located["geometry"]["coordinates"] == [-0.343, 51.752]
    assert next(f for f in geo["features"] if f["id"] == baseline["id"])["geometry"] is None
    for field in ("notes", "site"):
        tampered = copy.deepcopy(document)
        tampered["observations"][0][field] = "changed after export"
        assert not verify_export(tampered)["valid"]
    tampered = copy.deepcopy(document)
    tampered["audit_chain"][1]["event"]["timestamp"] = "altered"
    assert not verify_export(tampered)["valid"]
    tampered = copy.deepcopy(document)
    tampered["observations"][0]["review"]["note"] = "edited outside review"
    assert not verify_export(tampered)["valid"]


@pytest.mark.parametrize("ident,state,failed", [("control-blur", "retake", "detail"), ("control-glare", "retake", "glare"), ("control-dark", "retake", "exposure"), ("control-light", "lighting", None)])
def test_policy_changes_from_pixels(client, samples, ident, state, failed):
    baseline = submit(client, samples, "control-baseline").json()
    response = submit(client, samples, ident, reference_id=baseline["id"])
    assert response.status_code == 200
    record = response.json()
    assert record["policy"]["state"] == state
    if failed:
        assert not next(c["pass"] for c in record["quality"]["checks"] if c["key"] == failed)
        assert record["comparison"] is None
    else:
        assert record["comparison"]["lighting_confounded"]


def test_duplicate_and_different_site_do_not_establish_change(client, samples):
    baseline = submit(client, samples, "control-baseline").json()
    duplicate = submit(client, samples, "control-baseline", reference_id=baseline["id"]).json()
    assert duplicate["policy"]["state"] == "duplicate"
    unrelated = submit(client, samples, "control-change", site="Different place", reference_id=baseline["id"]).json()
    assert unrelated["policy"]["state"] == "different_site"
    assert unrelated["comparison"] is None


def test_failed_reference_is_not_a_valid_baseline(client, samples):
    blurred = submit(client, samples, "control-blur").json()
    current = submit(client, samples, "control-baseline", reference_id=blurred["id"]).json()
    assert current["policy"]["state"] == "unmatched"
    assert "failed" in current["comparison"]["reason"]


@pytest.mark.parametrize("metadata", [{"roi_confirmed": False}, {"roi_confirmed": "yes"}, {"latitude": 91, "longitude": 0}, {"latitude": 3}, {"latitude": True, "longitude": 2}, {"reference_id": {"bad": "type"}}])
def test_invalid_context_is_rejected_without_persistence(client, samples, metadata):
    assert submit(client, samples, "control-baseline", **metadata).status_code == 422
    assert client.get("/api/observations").json() == []


def test_invalid_images_roi_and_unknown_reference(client, samples):
    body = {"roi": "[0.2,0.2,0.8,0.8]", "metadata": '{"roi_confirmed":true}'}
    assert client.post("/api/analyze", files={"image": ("fake.png", b"not an image")}, data=body).status_code == 422
    for box in ([.9,.1,.1,.9], [0,0,.01,.01], [0,0,2,2], [0,0,1], [True,0,1,1]):
        body["roi"] = json.dumps(box)
        assert client.post("/api/analyze", files={"image": ("real.png", (ROOT/"samples/control-baseline.png").read_bytes())}, data=body).status_code == 422
    assert submit(client, samples, "control-baseline", reference_id="0"*16).status_code == 404
    assert client.get("/api/observations").json() == []


def test_provenance_is_verified_not_trusted_from_client(client, samples):
    record = submit(client, samples, "control-baseline", sample_id="river-ver").json()
    assert record["provenance"]["kind"] == "user_upload"
    for ident in ("river-ver", "river-liffey"):
        response = submit(client, samples, ident)
        assert response.status_code == 200
        assert response.json()["provenance"]["license"] == "CC0-1.0"
        assert not response.json()["provenance"]["field_validation"]


def test_auth_applies_to_images_lists_writes_and_exports(client, monkeypatch):
    monkeypatch.setenv("STREAMPROOF_TOKEN", "test-only-secret")
    assert client.get("/api/status").json()["authentication_required"]
    assert client.get("/").status_code == 200
    for endpoint in ("/api/samples", "/api/observations", "/api/export", "/api/samples/river-ver"):
        assert client.get(endpoint).status_code == 401
        assert client.get(endpoint, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/observations", headers={"Authorization": "Bearer test-only-secret"}).status_code == 200
    assert client.post("/api/analyze").status_code == 401


def test_export_format_and_missing_objects(client):
    assert client.get("/api/export?format=html").status_code == 422
    assert client.get("/api/observations/missing").status_code == 404
    assert client.get("/api/samples/missing").status_code == 404
    assert client.post("/api/observations/missing/review", json={"reviewer":"Test","assessment":"safe","note":"Unsupported safety claim"}).status_code == 422
    assert "no-store" in client.get("/api/observations").headers["cache-control"]

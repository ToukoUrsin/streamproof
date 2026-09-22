from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .vision import ImageRejected, MAX_BYTES, POLICY_VERSION, appearance, compare, decode_image, plan_next, quality, roi_mask

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("STREAMPROOF_DATA", ROOT / ".data"))
DATA.mkdir(parents=True, exist_ok=True)
(DATA / "images").mkdir(exist_ok=True)
DB = DATA / "observations.sqlite3"


def connection():
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, created TEXT, payload TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, previous_hash TEXT, event_hash TEXT)")
    return con


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append_audit(con, event):
    last = con.execute("SELECT event_hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    previous = last["event_hash"] if last else "0"*64
    event_hash = hashlib.sha256((previous + canonical(event)).encode()).hexdigest()
    con.execute("INSERT INTO audit(event,previous_hash,event_hash) VALUES(?,?,?)", (canonical(event), previous, event_hash))
    return event_hash


def get_record(ident):
    with connection() as con:
        row = con.execute("SELECT payload FROM observations WHERE id=?", (ident,)).fetchone()
    if row is None:
        raise HTTPException(404, "Observation not found.")
    return json.loads(row["payload"])


def all_records():
    with connection() as con:
        return [json.loads(r["payload"]) for r in con.execute("SELECT payload FROM observations ORDER BY created DESC")]


app = FastAPI(title="Streamproof", version="0.1.0", docs_url=None, redoc_url=None)


@app.middleware("http")
async def protect_operator_data(request: Request, call_next):
    token = os.environ.get("STREAMPROOF_TOKEN", "")
    if request.url.path.startswith("/api/") and request.url.path != "/api/status" and token:
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not secrets.compare_digest(supplied, token):
            return JSONResponse({"detail": "Enter the workspace access token to open observations."}, status_code=401)
    try:
        if int(request.headers.get("content-length", "0")) > MAX_BYTES + 100_000:
            return JSONResponse({"detail": "Request exceeds the 12 MB upload limit."}, status_code=413)
    except ValueError:
        return JSONResponse({"detail": "Invalid content length."}, status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    return response


@app.get("/api/status")
def status():
    return {"name": "Streamproof", "opencv": cv2.__version__, "policy": POLICY_VERSION, "authentication_required": bool(os.environ.get("STREAMPROOF_TOKEN")), "runtime": os.environ.get("STREAMPROOF_RUNTIME", "local"), "claims": "Image appearance evidence only; no water-safety assessment."}


def samples_manifest():
    return json.loads((ROOT / "samples" / "manifest.json").read_text())


@app.get("/api/samples")
def samples():
    return samples_manifest()


@app.get("/api/samples/{ident}")
def sample_image(ident: str):
    sample = next((s for s in samples_manifest() if s["id"] == ident), None)
    if not sample:
        raise HTTPException(404, "Sample not found.")
    return FileResponse(ROOT / "samples" / sample["file"])


@app.get("/api/observations")
def observations():
    return all_records()


@app.get("/api/observations/{ident}")
def observation(ident: str):
    return get_record(ident)


@app.get("/api/observations/{ident}/image")
def observation_image(ident: str, overlay: bool = False):
    record = get_record(ident)
    suffix = "-overlay.png" if overlay and record.get("overlay") else ".png"
    return FileResponse(DATA / "images" / (record["id"] + suffix))


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...), roi: str = Form(...), metadata: str = Form("{}")):
    start = time.perf_counter()
    try:
        box = json.loads(roi)
        meta = json.loads(metadata)
        if not isinstance(meta, dict):
            raise ValueError("Observation details must be an object.")
        if not isinstance(box, list) or not all(isinstance(v, (float, int)) and not isinstance(v, bool) for v in box):
            raise ValueError("Invalid water-region coordinates.")
        raw = await image.read(MAX_BYTES+1)
        decoded = decode_image(raw)
        mask = roi_mask(decoded.image, box)
        site = str(meta.get("site", "Unspecified site")).strip()[:120] or "Unspecified site"
        notes = str(meta.get("notes", ""))[:2500]
        if meta.get("roi_confirmed") is not True:
            raise ValueError("Confirm the selected rectangle contains the water area you intend to inspect.")
        reference_id = meta.get("reference_id")
        if reference_id is not None and (not isinstance(reference_id, str) or len(reference_id) != 16 or any(c not in "0123456789abcdef" for c in reference_id)):
            raise ValueError("Choose a valid saved reference observation.")
        lat, lon = meta.get("latitude"), meta.get("longitude")
        if (lat is None) != (lon is None):
            raise ValueError("Provide both latitude and longitude, or neither.")
        if lat is not None:
            if isinstance(lat, bool) or isinstance(lon, bool):
                raise ValueError("Coordinates must be numbers.")
            lat, lon = float(lat), float(lon)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("Coordinates are outside their valid ranges.")
    except (ValueError, TypeError, ImageRejected) as exc:
        raise HTTPException(422, str(exc)) from exc
    ident = uuid.uuid4().hex[:16]
    existing = all_records()
    duplicate = any(r["source_sha256"] == decoded.original_sha256 and r["site"] == site for r in existing)
    q = quality(decoded.image, mask)
    measures = appearance(decoded.image, mask)
    reference = get_record(meta["reference_id"]) if meta.get("reference_id") else None
    site_match = not reference or reference["site"] == site
    comparison, overlay = None, None
    if reference and site_match and q["accepted"] and reference["quality"]["accepted"]:
        refimage = cv2.imread(str(DATA / "images" / (reference["id"] + ".png")))
        if refimage is not None:
            comparison, overlay = compare(decoded.image, refimage, mask, roi_mask(refimage, reference["roi"]))
    elif reference and site_match and not reference["quality"]["accepted"]:
        comparison = {"comparable": False, "reason": "The reference image failed its quality checks.", "matches": 0}
    policy = plan_next(q, comparison, duplicate, site_match)
    provenance = {"kind": "user_upload", "label": "User supplied image", "license": "Not asserted by Streamproof", "field_validation": False}
    if meta.get("sample_id"):
        entry = next((s for s in samples_manifest() if s["id"] == meta["sample_id"]), None)
        if entry and hashlib.sha256((ROOT / "samples" / entry["file"]).read_bytes()).hexdigest() == decoded.original_sha256:
            provenance = entry["provenance"]
    record = {
        "id": ident, "created_at": utc_now(), "observed_at": str(meta.get("observed_at", ""))[:100] or None,
        "site": site, "notes": notes, "latitude": lat, "longitude": lon,
        "source_sha256": decoded.original_sha256,
        "normalized_sha256": hashlib.sha256(decoded.normalized).hexdigest(),
        "original_dimensions": decoded.original_size, "processed_dimensions": [decoded.image.shape[1], decoded.image.shape[0]],
        "roi": box, "roi_confirmed": True, "quality": q, "appearance": measures,
        "reference_id": reference["id"] if reference else None,
        "comparison": comparison, "policy": policy, "duplicate": duplicate,
        "overlay": overlay is not None, "opencv": cv2.__version__, "policy_version": POLICY_VERSION,
        "runtime": os.environ.get("STREAMPROOF_RUNTIME", "local"),
        "processing_ms": round((time.perf_counter()-start)*1000, 1),
        "provenance": provenance, "review": None,
        "limitations": ["Appearance is not water chemistry or water safety.", "Thresholds are heuristic and not field-calibrated.", "No disease, pollution-source or organism identification is performed.", "An image hash proves byte identity, not capture time or authenticity."],
    }
    (DATA / "images" / (ident + ".png")).write_bytes(decoded.normalized)
    # Raw uploads stay private and never form part of public exports.
    (DATA / "images" / (ident + ".source")).write_bytes(raw)
    if overlay is not None:
        cv2.imwrite(str(DATA / "images" / (ident + "-overlay.png")), overlay)
    # The immutable evidence has a separate hash so reviews can evolve while
    # its integrity remains checkable against an exported observation.
    record["evidence_hash"] = hashlib.sha256(canonical({k: v for k, v in record.items() if k != "review"}).encode()).hexdigest()
    with connection() as con:
        con.execute("BEGIN IMMEDIATE")
        record["audit_hash"] = append_audit(con, {"type": "observation", "schema": 2, "id": ident, "timestamp": record["created_at"], "payload_hash": record["evidence_hash"]})
        con.execute("INSERT INTO observations VALUES(?,?,?)", (ident, record["created_at"], canonical(record)))
    return record


class Review(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    assessment: str = Field(pattern="^(more_evidence|appearance_noted|no_visible_concern|inconclusive)$")
    note: str = Field(min_length=3, max_length=2000)


@app.post("/api/observations/{ident}/review")
def review(ident: str, review: Review):
    record = get_record(ident)
    record["review"] = {**review.model_dump(), "at": utc_now(), "water_safety": "not_assessed"}
    with connection() as con:
        con.execute("BEGIN IMMEDIATE")
        record["audit_hash"] = append_audit(con, {"type": "human_review", "id": ident, "review": record["review"]})
        con.execute("UPDATE observations SET payload=? WHERE id=?", (canonical(record), ident))
    return record


@app.get("/api/export")
def export(format: str = "json", site: str | None = None):
    records = [r for r in all_records() if site is None or r["site"] == site]
    if format == "geojson":
        content = {"type": "FeatureCollection", "name": "Streamproof observations", "notice": "No water-safety classifications. Null geometry means location was not supplied.", "features": [
            {"type": "Feature", "id": r["id"], "geometry": {"type": "Point", "coordinates": [r["longitude"], r["latitude"]]} if r["latitude"] is not None else None,
             "properties": {k: r[k] for k in ("site", "created_at", "observed_at", "source_sha256", "roi", "quality", "comparison", "policy", "review", "provenance")}}
            for r in records]}
        media = "application/geo+json"
    elif format == "json":
        with connection() as con:
            # The full chain provides context; no images or credentials are exported.
            chain = [dict(r) for r in con.execute("SELECT * FROM audit ORDER BY id")]
        for row in chain:
            row["event"] = json.loads(row["event"])
        content = {"schema": "streamproof-evidence/1", "exported_at": utc_now(), "observations": records, "audit_chain": chain,
                   "integrity_scope": "Locally hash-linked records, not external attestation. No proof of capture authenticity, time or location.", "water_safety": "not_assessed"}
        media = "application/json"
    else:
        raise HTTPException(422, "Export format must be json or geojson.")
    return Response(json.dumps(content, indent=2, ensure_ascii=False), media_type=media, headers={"Content-Disposition": f'attachment; filename="streamproof-evidence.{format}"'})


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="ui")

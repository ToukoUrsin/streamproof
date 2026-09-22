"""Verify an exported local evidence chain without a running server."""
from __future__ import annotations

import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def verify_export(document: dict) -> dict:
    """Detect changed/missing/reordered exported events and edited observations.

    A complete database rewrite or truncated tail cannot be detected without an
    externally retained trusted final hash. This is integrity, not authenticity.
    """
    failures, previous, events = [], "0" * 64, {}
    for index, row in enumerate(document.get("audit_chain", []), 1):
        expected = hashlib.sha256((previous + canonical(row["event"])).encode()).hexdigest()
        if row["previous_hash"] != previous or row["event_hash"] != expected:
            failures.append(f"Event {index}: broken hash link or edited event")
        previous = row["event_hash"]
        if row["event"]["type"] == "observation":
            events[row["event"]["id"]] = row["event"]
    for record in document.get("observations", []):
        event = events.get(record["id"])
        if event is None:
            failures.append(f"Observation {record['id']}: no creation event")
            continue
        immutable = {k: v for k, v in record.items() if k not in {"audit_hash", "evidence_hash", "review"}}
        if event.get("schema", 1) < 2:
            immutable["review"] = None
        digest = hashlib.sha256(canonical(immutable).encode()).hexdigest()
        if digest != event["payload_hash"] or record.get("evidence_hash", digest) != digest:
            failures.append(f"Observation {record['id']}: evidence payload changed")
        reviews = [r["event"]["review"] for r in document.get("audit_chain", []) if r["event"]["type"] == "human_review" and r["event"]["id"] == record["id"]]
        if record.get("review") != (reviews[-1] if reviews else None):
            failures.append(f"Observation {record['id']}: review does not match latest event")
    return {"valid": not failures, "failures": failures, "events": len(document.get("audit_chain", [])), "observations": len(document.get("observations", [])), "final_hash": previous, "scope": "Local integrity only. No authenticity, capture-time or location attestation."}

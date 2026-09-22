"""Reproducible engineering checks, explicitly not environmental validation."""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

from streamproof.vision import compare, decode_image, plan_next, quality, roi_mask

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="artifacts/control-evaluation.json")
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
samples = json.loads((root / "samples/manifest.json").read_text())
baseline = decode_image((root / "samples/control-baseline.png").read_bytes()).image
baseline_mask = roi_mask(baseline, [.32,.32,.68,.94])
results = []
for sample in samples:
    start = time.perf_counter()
    current = decode_image((root / "samples" / sample["file"]).read_bytes()).image
    mask = roi_mask(current, sample["roi"])
    checks = quality(current, mask)
    comparison = None
    if sample["provenance"]["kind"] == "synthetic_fixture" and checks["accepted"]:
        comparison, _ = compare(current, baseline, mask, baseline_mask)
    policy = plan_next(checks, comparison, False)
    results.append({"sample": sample["id"], "kind": sample["provenance"]["kind"], "quality": checks, "comparison": comparison, "policy": policy["state"], "processing_ms": round((time.perf_counter()-start)*1000, 1)})
report = {"generated_at": datetime.now(timezone.utc).isoformat(), "opencv": cv2.__version__, "python": platform.python_version(), "platform": platform.platform(), "field_validation": False, "scope": "Programmed controls exercise known branches; historical images demonstrate single-image processing. No sensitivity, specificity or water-quality accuracy claim.", "results": results}
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2)+"\n")
for result in results:
    print(f"{result['sample']}: {result['policy']} ({result['processing_ms']} ms)")
print(f"Saved {output}")

"""Deterministic, inspectable OpenCV measurements; no water-safety classifier.

Every threshold is an engineering heuristic, not a calibrated environmental
limit. Comparisons require image alignment and matching observation metadata.
"""
from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 24_000_000
MAX_BYTES = 12 * 1024 * 1024
PROCESS_SIDE = 1400
POLICY_VERSION = "observation-policy/1.0"


class ImageRejected(ValueError):
    pass


@dataclass
class Decoded:
    image: np.ndarray
    normalized: bytes
    original_sha256: str
    original_size: tuple[int, int]


def decode_image(raw: bytes) -> Decoded:
    if not raw or len(raw) > MAX_BYTES:
        raise ImageRejected("Use a JPEG or PNG smaller than 12 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in {"JPEG", "PNG"}:
                raise ImageRejected("Only JPEG and PNG images are supported.")
            if source.width * source.height > MAX_PIXELS:
                raise ImageRejected("Image exceeds the 24 megapixel limit.")
            if min(source.size) < 64:
                raise ImageRejected("Image must be at least 64 pixels on each side.")
            original_size = source.size
            source.load()
            display = ImageOps.exif_transpose(source).convert("RGB")
            display.thumbnail((PROCESS_SIDE, PROCESS_SIDE), Image.Resampling.LANCZOS)
            image = cv2.cvtColor(np.array(display), cv2.COLOR_RGB2BGR)
            success, encoded = cv2.imencode(".png", image)
            if not success:
                raise ImageRejected("Could not normalize the image.")
            return Decoded(image, encoded.tobytes(), hashlib.sha256(raw).hexdigest(), original_size)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageRejected("The file could not be decoded as a safe JPEG or PNG.") from exc


def roi_mask(image: np.ndarray, roi: list[float]) -> np.ndarray:
    if len(roi) != 4 or not all(math.isfinite(v) and 0 <= v <= 1 for v in roi):
        raise ValueError("Water region must contain four normalized coordinates.")
    x1, y1, x2, y2 = roi
    if x2 - x1 < 0.03 or y2 - y1 < 0.03 or (x2 - x1) * (y2 - y1) < 0.005:
        raise ValueError("Select a larger water region (at least 0.5% of the image).")
    h, w = image.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    mask[round(y1*h):round(y2*h), round(x1*w):round(x2*w)] = 255
    return mask


def quality(image: np.ndarray, mask: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    pixels = mask > 0
    # Edges of the selected rectangle must not inflate sharpness.
    inner = cv2.erode(mask, np.ones((5, 5), np.uint8)) > 0
    if not inner.any():
        inner = pixels
    sharpness = float(np.var(cv2.Laplacian(gray, cv2.CV_64F)[inner]))
    dark = float(np.mean(gray[pixels] < 20))
    clipped = float(np.mean(gray[pixels] > 248))
    glare = float(np.mean((hsv[:, :, 2][pixels] > 225) & (hsv[:, :, 1][pixels] < 32)))
    checks = [
        {"key": "detail", "label": "Image detail", "value": round(sharpness, 1), "unit": "Laplacian variance", "pass": sharpness >= 22, "note": "Low detail can be blur or naturally smooth water; retake before comparison."},
        {"key": "exposure", "label": "Exposure", "value": round((dark+clipped)*100, 1), "unit": "% clipped pixels", "pass": dark+clipped < .24, "note": "Very dark or saturated pixels hide visible detail."},
        {"key": "glare", "label": "Bright reflections", "value": round(glare*100, 1), "unit": "% of region", "pass": glare < .23, "note": "Bright, low-saturation pixels are a reflection proxy, not a water measurement."},
        {"key": "resolution", "label": "Selected area", "value": int(np.sum(pixels)), "unit": "pixels", "pass": int(np.sum(pixels)) >= 8000, "note": "A useful selected area makes repeat comparisons less fragile."},
    ]
    return {"accepted": all(c["pass"] for c in checks), "checks": checks, "mean_brightness": round(float(np.mean(gray[pixels])), 2)}


def appearance(image: np.ndarray, mask: np.ndarray) -> dict:
    px = mask > 0
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    edge = cv2.Canny(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 60, 150)
    median = np.median(rgb[px], axis=0).astype(int).tolist()
    hist = cv2.calcHist([hsv], [0, 1], mask, [18, 8], [0, 180, 0, 256])
    cv2.normalize(hist, hist, norm_type=cv2.NORM_L1)
    return {
        "median_rgb": median,
        "median_hex": "#" + "".join(f"{v:02x}" for v in median),
        "median_lab": np.round(np.median(lab[px], axis=0), 2).tolist(),
        "saturation": round(float(np.median(hsv[:, :, 1][px])) / 255 * 100, 1),
        "edge_density": round(float(np.mean(edge[px] > 0))*100, 2),
        "histogram": np.round(hist.flatten(), 7).tolist(),
        "description": "Visible appearance only. Lighting, depth, reflections and camera settings can cause changes.",
    }


def compare(current: np.ndarray, reference: np.ndarray, current_mask: np.ndarray, reference_mask: np.ndarray) -> tuple[dict, np.ndarray | None]:
    """Register using scene structure outside water, then intersect water ROIs."""
    gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
    refgray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=2400)
    k1, d1 = orb.detectAndCompute(refgray, cv2.bitwise_not(reference_mask))
    k2, d2 = orb.detectAndCompute(gray, cv2.bitwise_not(current_mask))
    rejected = {"comparable": False, "reason": "Not enough stable bank features to align these views.", "matches": 0}
    if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
        return rejected, None
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1, d2, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < .72*pair[1].distance]
    if len(good) < 12:
        return {**rejected, "matches": len(good)}, None
    src = np.float32([k1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([k2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    transform, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    ratio = float(np.mean(inliers)) if inliers is not None else 0
    if transform is None or not np.isfinite(transform).all() or ratio < .55:
        return {**rejected, "matches": len(good), "inlier_ratio": round(ratio, 3)}, None
    h, w = gray.shape
    warped = cv2.warpPerspective(reference, transform, (w, h))
    warped_mask = cv2.warpPerspective(reference_mask, transform, (w, h), flags=cv2.INTER_NEAREST)
    overlap = cv2.bitwise_and(current_mask, warped_mask)
    overlap_fraction = float(np.count_nonzero(overlap))/max(1, np.count_nonzero(current_mask))
    if overlap_fraction < .65:
        return {**rejected, "reason": "The selected water regions do not overlap enough after alignment.", "matches": len(good), "overlap_fraction": round(overlap_fraction, 3)}, None
    a = appearance(current, overlap)
    b = appearance(warped, overlap)
    distance = float(cv2.compareHist(np.array(a["histogram"], np.float32), np.array(b["histogram"], np.float32), cv2.HISTCMP_BHATTACHARYYA))
    # Lab pixel changes are exploratory, not physical turbidity/chlorophyll units.
    lab1 = cv2.cvtColor(current, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab2 = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB).astype(np.float32)
    delta = np.linalg.norm(lab1-lab2, axis=2)
    visible = overlap > 0
    changed = (delta > 30) & visible
    brightness_shift = abs(float(np.mean(gray[visible])) - float(np.mean(cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)[visible])))
    # Compare non-water background to distinguish global exposure from local changes.
    bank = (current_mask == 0) & (cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY) > 0)
    bank_shift = float(np.median(delta[bank])) if bank.any() else 255.
    overlay = current.copy()
    overlay[changed] = (.4*overlay[changed] + .6*np.array([68, 172, 244])).astype(np.uint8)
    return {
        "comparable": True,
        "reason": "Views aligned using stable features outside the selected water area.",
        "matches": len(good), "inlier_ratio": round(ratio, 3),
        "overlap_fraction": round(overlap_fraction, 3),
        "histogram_distance": round(distance, 4),
        "changed_fraction": round(float(np.mean(changed[visible])), 4),
        "median_lab_distance": round(float(np.median(delta[visible])), 2),
        "brightness_shift": round(brightness_shift, 2),
        "background_shift": round(bank_shift, 2),
        "lighting_confounded": bank_shift > 20 or brightness_shift > 45,
        "notice": "Not calibrated water quality. Same-view appearance differences require contextual human review.",
    }, overlay


def plan_next(q: dict, comparison: dict | None, duplicate: bool, site_match: bool = True) -> dict:
    steps = []
    failed = [c for c in q["checks"] if not c["pass"]]
    steps.append({"tool": "quality_gate", "observation": f"{len(q['checks'])-len(failed)} of {len(q['checks'])} checks pass", "decision": "stop_for_better_evidence" if failed else "continue"})
    if failed:
        keys = [c["key"] for c in failed]
        instruction = "Hold the camera steady and include textured bank features."
        if "glare" in keys:
            instruction = "Move slightly to avoid bright sky reflections; keep the same bank landmarks in view."
        elif "exposure" in keys:
            instruction = "Retake with balanced exposure; avoid deep shadow and clipped highlights."
        elif "resolution" in keys:
            instruction = "Select a larger water region or upload a higher-resolution photo."
        return {"state": "retake", "title": "One better photo first.", "summary": "The image does not support a reliable comparison yet.", "request": instruction, "severity": "amber", "trace": steps}
    if duplicate:
        steps.append({"tool": "sha256_check", "observation": "The exact source bytes already exist in this case", "decision": "request_independent_capture"})
        return {"state": "duplicate", "title": "Same file. No new evidence.", "summary": "This upload cannot count as an independent repeat observation.", "request": "Capture a new image at the site; do not re-upload or edit the same file.", "severity": "amber", "trace": steps}
    if not site_match:
        steps.append({"tool": "site_context", "observation": "The selected reference belongs to a different site", "decision": "reject_comparison"})
        return {"state": "different_site", "title": "These are different places.", "summary": "Cross-site photos cannot establish a local change.", "request": "Choose a reference from this site, or save this as its first observation.", "severity": "amber", "trace": steps}
    if comparison is None:
        steps.append({"tool": "reference_check", "observation": "No earlier observation selected", "decision": "establish_baseline"})
        return {"state": "baseline", "title": "A useful first observation.", "summary": "Keep this view as the starting point for a repeat visit.", "request": "Take a repeat photo from the same viewpoint and similar light. Include stable bank landmarks.", "severity": "green", "trace": steps}
    steps.append({"tool": "align_bank_features", "observation": comparison["reason"], "decision": "compare_appearance" if comparison["comparable"] else "request_matched_view"})
    if not comparison["comparable"]:
        return {"state": "unmatched", "title": "Match the viewpoint first.", "summary": "We cannot honestly compare these water regions.", "request": "Retake from the earlier camera position with the same bank landmarks visible.", "severity": "amber", "trace": steps}
    steps.append({"tool": "check_lighting", "observation": f"Background appearance shift {comparison['background_shift']:.1f}", "decision": "request_matched_light" if comparison["lighting_confounded"] else "continue"})
    if comparison["lighting_confounded"]:
        return {"state": "lighting", "title": "Light may explain the difference.", "summary": "A global image change makes this comparison inconclusive.", "request": "Repeat with similar light and exposure. Do not interpret this as a change in the water.", "severity": "amber", "trace": steps}
    changed = comparison["changed_fraction"] > .14 and comparison["histogram_distance"] > .15
    steps.append({"tool": "measure_appearance", "observation": f"{comparison['changed_fraction']*100:.1f}% of overlapping pixels exceeded the display-distance threshold", "decision": "request_confirmation" if changed else "queue_human_review"})
    if changed:
        return {"state": "change", "title": "Something looks different here.", "summary": "A visible difference survived the alignment and lighting checks. Its cause is unknown.", "request": "Capture a close view plus one upstream view. Record recent rain, shade and camera changes; a person must assess the evidence.", "severity": "amber", "trace": steps}
    return {"state": "review", "title": "Ready for a human second look.", "summary": "No large appearance difference passed this policy. This does not establish water safety.", "request": "Review the paired photos and context, then record an assessment or request more evidence.", "severity": "green", "trace": steps}

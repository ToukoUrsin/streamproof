import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from streamproof.vision import ImageRejected, compare, decode_image, plan_next, quality, roi_mask

ROOT = Path(__file__).resolve().parent.parent


def image(name):
    return decode_image((ROOT / "samples" / (name + ".png")).read_bytes()).image


def test_reencoded_unchanged_scene_goes_to_human_review():
    reference = image("control-baseline")
    success, encoded = cv2.imencode(".jpg", reference, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert success
    current = decode_image(encoded.tobytes()).image
    mask = roi_mask(current, [.32,.32,.68,.94])
    comparison, overlay = compare(current, reference, mask, mask)
    assert comparison["comparable"]
    assert comparison["changed_fraction"] < .01
    assert plan_next(quality(current, mask), comparison, False)["state"] == "review"
    assert overlay is not None


def test_missing_bank_features_rejects_alignment():
    current = np.full((500, 700, 3), 100, np.uint8)
    mask = roi_mask(current, [.25,.25,.75,.75])
    comparison, overlay = compare(current, current, mask, mask)
    assert not comparison["comparable"] and overlay is None


def test_disjoint_water_regions_reject_comparison():
    current = image("control-baseline")
    mask = roi_mask(current, [.32,.65,.68,.94])
    earlier_mask = roi_mask(current, [.32,.20,.68,.40])
    comparison, overlay = compare(current, current, mask, earlier_mask)
    assert not comparison["comparable"]
    assert "overlap" in comparison["reason"]
    assert overlay is None


def test_normalization_removes_metadata_and_rotates_exif():
    source = Image.new("RGB", (80, 120), (120, 150, 80))
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "Private annotation should not enter served preview"
    buffer = io.BytesIO()
    source.save(buffer, format="JPEG", exif=exif)
    decoded = decode_image(buffer.getvalue())
    normalized = Image.open(io.BytesIO(decoded.normalized))
    assert decoded.original_size == (80, 120)
    assert normalized.size == (120, 80)
    assert not normalized.getexif()
    assert b"Private annotation" not in decoded.normalized


@pytest.mark.parametrize("kind", ["tiny", "unsupported", "oversize"])
def test_decode_limits(kind):
    if kind == "oversize":
        raw = b"x" * (12*1024*1024 + 1)
    else:
        buffer = io.BytesIO()
        Image.new("RGB", (20,20) if kind == "tiny" else (100,100)).save(buffer, format="PNG" if kind == "tiny" else "GIF")
        raw = buffer.getvalue()
    with pytest.raises(ImageRejected):
        decode_image(raw)

# Evaluation — September 21, 2026

**24 tests passed** in 10.07 seconds using Python 3.14.7 and OpenCV 5.0.0 on the development Mac. Two upstream deprecation warnings concern Starlette/httpx and an AnyIO alias; no test failures remained. Reproduce with `python -m pytest -q` after installing `requirements-dev.txt`.

The actual serialized control run is [control-evaluation.json](../artifacts/control-evaluation.json), created by `python -m scripts.evaluate_controls`. It contains version/platform/date, full measurements and observed policy results.

| Input | Observed branch | What the check establishes |
|---|---|---|
| Baseline compared with itself | Human review; zero changed pixels | Identical normalized scenes do not trigger change |
| Controlled local color patch | Change; 66.97% changed pixels; 2,393 matches | A known local appearance difference changes the next request |
| Strong blur | Retake; detail gate fails | Blurred evidence stops before comparison |
| Artificial reflection patch | Retake; glare/exposure fail | Large bright regions stop comparison |
| Darkened frame | Retake; exposure/detail fail | Missing visible information stops comparison |
| Global brightness shift | Matched-light request | A global appearance shift is not called a local water change |
| Historical River Ver photo | Baseline | Real public JPEG processing works |
| Historical River Liffey official preview | Baseline | A second licensed real photo processes successfully |

The engineering run took approximately 85–1,000 ms per image on this machine. This includes the applicable image tools, not network or cloud latency. These observations are not a benchmark guarantee.

HTTP integration checks cover actual multipart image ingestion, immutable evidence storage, overlays, human review, source provenance verification, JSON/GeoJSON export, null-location handling, invalid context/image/ROI rejection, a failed reference, same-file duplicates, cross-site comparison rejection, token protection and tamper detection. Vision checks additionally cover unchanged JPEG recompression, missing scene features, disjoint water regions, EXIF orientation and removal of preview metadata, tiny files, unsupported formats and upload-size limits.

Browser verification exercised the default historical photo, control-pair setup, real processing, changed-region overlay, human review dialog/save, saved read-only context and export dialog. The displayed result matched the backend: 67.0% changed pixels and the close/upstream-photo request. Saved review was visibly confirmed.

## What this does not establish

The programmed controls were deliberately built to exercise known branches; no held-out field dataset, expert labeling, sensitivity/specificity evaluation, intervention outcome or chemical measurement exists. Historical photos are unpaired and demonstrate processing only. No environmental accuracy, safety, ecological health, adoption or impact metric is claimed.

A useful field study would prospectively collect repeated viewpoints across light, weather and device conditions, annotate usable/unusable comparisons with environmental experts, report false-change and missed-change rates, and compare contextual photo triage against a volunteer workflow. Instrumented water measurements would be required before investigating any relationship to physical conditions. This remains future work.

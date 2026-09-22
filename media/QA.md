# Recorded walkthrough verification

Checked September 21, 2026, after assembly of the actual prototype captures.

- Final file: `streamproof-demo.mp4`, 196.166 seconds, 11,238,784 bytes.
- Picture: H.264, 1920 × 1080, 30 frames/second. Sound: AAC. English subtitle track included; standalone SRT available.
- The entire video and audio streams decoded through FFmpeg successfully, with no decoding error reported.
- Audio peak: −2.7 dBFS; mean: −24.5 dBFS. No clipping detected by peak inspection.
- Reviewed encoded frames from the historical baseline, the 67% synthetic change, lighting confound, blur retake, explicitly AI-assisted demo assessment, and method explanation.
- Selected real-frame holds keep the relevant evidence visible during narration. The completed-baseline frame and the 34 ms capture-delivery ordering adjustment are documented in `edit-manifest.json`.
- SHA-256: `e75544839ff131b5b350bfc028732ce923a454b42a174a0bde6caedd1e8096b0`.

This verifies the media artifact, not field accuracy or submission acceptance. The recording shows the local runtime. Application validation and its limits are recorded separately in `docs/EVALUATION.md`.

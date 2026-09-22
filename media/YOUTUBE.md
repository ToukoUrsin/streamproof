# Upload metadata

## Title

Streamproof — A better second look | Working prototype

## Description

A photograph can raise a question. A careful record helps people answer it.

Streamproof is a citizen stream-observation notebook built with OpenCV 5. It checks photo quality, aligns repeat views using bank features, measures visible appearance, and requests the next useful observation. A person retains responsibility for interpretation.

Source and local setup: https://github.com/ToukoUrsin/streamproof

This walkthrough records the actual local prototype. It begins with a historical CC0 photograph of the River Ver, then uses explicitly labeled programmed controls. The deliberate recoloring, lighting shift and blur produce different measured results and next requests. The review is signed as an AI-assisted demo operator and describes the synthetic recoloring; it is not a human field assessment.

00:00 A better second look
00:25 A useful baseline
00:52 Follow the difference
01:24 Check the light
01:51 Ask for a better image
02:15 Record an interpretation
02:43 Keep the evidence

The recorded evidence export passed a separate consistency verifier with six linked audit events and five observations. The prototype has 24 passing local tests. These checks do not establish field accuracy, capture authenticity, verified location, or water safety. Image differences are not measurements of chemistry. Field calibration and expert evaluation remain future work. No AWS runtime or submission acceptance is claimed.

AI disclosure: OpenAI Codex assisted with research, design, implementation, tests, narration and demo preparation. The product uses OpenCV measurements and a deterministic policy, with no LLM inference dependency. Narration is an ElevenLabs stock synthetic voice; no personal voice was cloned. Python/Pillow and FFmpeg assemble actual recorded application frames with explanatory holds. Media provenance and source licenses are documented in the repository.

## Files

- Upload `streamproof-demo.mp4`, approximately 3:16, H.264 / AAC at 1920 × 1080.
- Optional English caption file: `streamproof-demo.srt` (approximate cue timing).
- Reproducible edit decisions: `edit-manifest.json`, `pacing.json`, `assemble.py`.

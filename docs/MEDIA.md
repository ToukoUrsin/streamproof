# Media provenance

Both photographs were downloaded from Wikimedia Commons on September 21, 2026. Their file pages explicitly identify CC0 licensing. The untouched downloaded representations are preserved in `samples/`; metadata and SHA-256 hashes are in the adjacent JSON files and the sample manifest. The River Liffey original matches Wikimedia’s published SHA-1 but is truncated and fails strict Pillow decoding. The app therefore uses Wikimedia’s official 1280-pixel JPEG preview, which passes strict decoding; the original is preserved separately under `samples/source-originals/`. No decoder safety check was weakened.

| File | Author | License and source |
|---|---|---|
| `river-ver.jpg` | Gary Houston | [River-Ver-20050409-012.jpg](https://commons.wikimedia.org/wiki/File:River-Ver-20050409-012.jpg), [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `river-liffey.jpg` | Dave Meier | [River-liffey.jpg](https://commons.wikimedia.org/wiki/File:River-liffey.jpg), [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

These are historical photographs of different rivers, not paired repeats and not current incident reports. They may be processed individually. Comparing them cannot validate change detection, nor validate any water-quality inference.

The six `control-*.png` files are generated programmatically by `scripts/make_fixtures.py` with a fixed random seed. Each contains an explicit synthetic label. Their deliberately controlled changes let tests exercise specific paths. They do not represent physical measurement, a real water event, or field validation. The generator and its output are MIT-licensed with the original code.

The UI uses system fonts and an original simple wave icon. No external analytics, fonts or stock illustration services load in the app.

## Demonstration video

The narrated walkthrough records the actual local prototype. It starts with the historical River Ver photograph, then uses explicitly labeled programmed controls to demonstrate visible change, lighting confounds and blur. The recorded assessment is signed “Demo operator (AI-assisted)” and describes the deliberate recoloring. This is a demonstration of the review workflow, not a human field assessment. The footage makes no water-chemistry, field-validation or AWS-runtime claim.

The seven narration files in `media/` are spoken by an ElevenLabs stock synthetic voice; no personal voice was cloned. OpenAI Codex assisted with narration, capture coordination and assembly. Python/Pillow and FFmpeg produce chapter bars, edit the real captures, and package H.264 video, AAC narration and English captions. The video helper adapts the author's MIT-licensed Counterseed media assembler; it is not application code or an external inference service.

`media/assemble.py` reads original timestamped frames from `media/raw/sceneN*/frames.json`. Suffix chunks continue the corresponding chapter in order. `media/edit-manifest.json` records chapter purpose and reuse of the actual completed-baseline frame from the beginning of the next capture. Idle time between separately recorded chunks is removed; `media/pacing.json` holds selected actual frames under their explanations. It never generates an application state or fabricates an interaction. Subtitle text matches the narration, with approximate word-count cue timing. Raw captures, audio, rendered chapters and the final video remain outside Git; narration, pacing, captions and the renderer are published.

To regenerate with the original assets, run `python3 media/assemble.py` using Python with Pillow, FFmpeg and FFprobe. Video encoding is capped at two threads.

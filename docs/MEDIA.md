# Media provenance

Both photographs were downloaded from Wikimedia Commons on September 21, 2026. Their file pages explicitly identify CC0 licensing. The untouched downloaded representations are preserved in `samples/`; metadata and SHA-256 hashes are in the adjacent JSON files and the sample manifest. The River Liffey original matches Wikimedia’s published SHA-1 but is truncated and fails strict Pillow decoding. The app therefore uses Wikimedia’s official 1280-pixel JPEG preview, which passes strict decoding; the original is preserved separately under `samples/source-originals/`. No decoder safety check was weakened.

| File | Author | License and source |
|---|---|---|
| `river-ver.jpg` | Gary Houston | [River-Ver-20050409-012.jpg](https://commons.wikimedia.org/wiki/File:River-Ver-20050409-012.jpg), [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `river-liffey.jpg` | Dave Meier | [River-liffey.jpg](https://commons.wikimedia.org/wiki/File:River-liffey.jpg), [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

These are historical photographs of different rivers, not paired repeats and not current incident reports. They may be processed individually. Comparing them cannot validate change detection, nor validate any water-quality inference.

The six `control-*.png` files are generated programmatically by `scripts/make_fixtures.py` with a fixed random seed. Each contains an explicit synthetic label. Their deliberately controlled changes let tests exercise specific paths. They do not represent physical measurement, a real water event, or field validation. The generator and its output are MIT-licensed with the original code.

The UI uses system fonts and an original simple wave icon. No external analytics, fonts or stock illustration services load in the app.

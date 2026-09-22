"""Usage: python -m scripts.verify_export path/to/export.json"""
import json
import sys
from pathlib import Path
from streamproof.integrity import verify_export

result = verify_export(json.loads(Path(sys.argv[1]).read_text()))
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["valid"] else 1)

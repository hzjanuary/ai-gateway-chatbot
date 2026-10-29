"""Run via python stdin inside actual release image; no added scanner dependencies."""

import hashlib
import importlib.metadata
import json
from pathlib import Path

packages = []
for dist in importlib.metadata.distributions():
    meta = dist.metadata
    licenses = []
    for path in dist.files or []:
        if "license" in str(path).lower() or "copying" in str(path).lower():
            full = Path(dist.locate_file(path))
            if full.is_file() and full.stat().st_size < 100000:
                licenses.append({"path": str(path), "text": full.read_text(errors="replace")})
    supplement_dir = Path("/app/third-party-licenses")
    if (supplement_dir / "manifest.json").exists():
        for extra in json.loads((supplement_dir / "manifest.json").read_text()):
            if extra["name"] == meta["Name"].lower() and extra["version"] == meta["Version"]:
                path = supplement_dir / extra["file"]
                assert hashlib.sha256(path.read_bytes()).hexdigest() == extra["sha256"]
                licenses.append(
                    {
                        "path": str(path),
                        "text": path.read_text(),
                        "source": extra["source"],
                        "sha256": extra["sha256"],
                    }
                )
    packages.append(
        {
            "name": meta["Name"],
            "version": meta["Version"],
            "license_expression": meta.get("License-Expression"),
            "license": meta.get("License"),
            "classifiers": meta.get_all("Classifier", []),
            "license_files": licenses,
        }
    )
print(json.dumps(sorted(packages, key=lambda item: item["name"].lower()), indent=2))

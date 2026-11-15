"""Translation pipeline: extract tr() strings, merge Arabic catalog, build .qm.

Usage:
    python scripts/update_translations.py            # extract + merge + release
    python scripts/update_translations.py --extract-only   # only regenerate app_ar.ts

Pipeline:
  1. lupdate scans app/ + main.py for tr() calls -> resources/i18n/app_ar.ts
  2. Translations from resources/i18n/ar_strings.json (flat source->Arabic map)
     are merged into every context whose <source> matches a key.
  3. lrelease compiles app_ar.ts -> app_ar.qm (loaded at runtime by app.ui.i18n).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "resources" / "i18n"
TS_FILE = I18N_DIR / "app_ar.ts"
QM_FILE = I18N_DIR / "app_ar.qm"
JSON_FILE = I18N_DIR / "ar_strings.json"


def _tool(name: str) -> str:
    import PySide6

    base = os.path.dirname(PySide6.__file__)
    exe = os.path.join(base, f"{name}.exe" if os.name == "nt" else name)
    if not os.path.exists(exe):
        raise SystemExit(f"{name} not found at {exe} (PySide6 installation issue)")
    return exe


def run_lupdate() -> None:
    # PySide6 lupdate does not auto-detect .py files in directory scans:
    # pass every Python source file explicitly.
    py_files = sorted(
        p for p in (ROOT / "app").rglob("*.py") if "__pycache__" not in p.parts
    )
    py_files.append(ROOT / "main.py")
    cmd = [_tool("lupdate"), *[str(p) for p in py_files], "-ts", str(TS_FILE)]
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def merge_translations() -> int:
    """Fill <translation> nodes from ar_strings.json; returns merged count."""
    catalog = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    tree = ET.parse(TS_FILE)
    root = tree.getroot()
    merged = 0
    for message in root.iter("message"):
        source = message.find("source")
        translation = message.find("translation")
        if source is None or translation is None:
            continue
        text = source.text or ""
        if text in catalog:
            translation.text = catalog[text]
            if "unfinished" in (translation.get("type") or ""):
                del translation.attrib["type"]
            merged += 1
    ET.indent(tree, space="  ")
    tree.write(TS_FILE, encoding="utf-8", xml_declaration=True)
    return merged


def run_lrelease() -> None:
    cmd = [_tool("lrelease"), str(TS_FILE), "-qm", str(QM_FILE)]
    print(">>", " ".join(cmd))
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(result.stdout.strip())


def main() -> int:
    I18N_DIR.mkdir(parents=True, exist_ok=True)
    if "--extract-only" in sys.argv:
        run_lupdate()
        print(f"Wrote {TS_FILE}")
        return 0
    run_lupdate()
    merged = merge_translations()
    print(f"Merged {merged} translations into {TS_FILE}")
    run_lrelease()
    print(f"Compiled {QM_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

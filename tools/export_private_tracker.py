#!/usr/bin/env python3
"""Pack a ready-to-init private tracker tree. Does not create a Git remote and does not
delete or modify files in this public checkout.

  python3 tools/export_private_tracker.py /path/floorline-private-tracker.tar.gz
"""
import io, os, tarfile, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "floorline-private-tracker"

INCLUDE = [
    "tracker/build_tracker.py",
    "tracker/test_tracker.py",
    "tracker/sheet_logic.py",
    "tracker/verify_engine.py",
    "tracker/gen_presets_tab.py",
    "tracker/FORMULAS.md",
    "tracker/presets_tab.csv",
    "tracker/golden_map.json",
    "golden/oracle.py",
    "golden/cases.json",
    "data/contracts.json",
    "data/presets.json",
    "docs/CME-TICKS.md",
    "docs/DEPLOY-CHECKLIST.md",
    "docs/GUMROAD-FILE-REPLACE.md",
    "docs/PRIVATE-TRACKER-MIGRATION.md",
    "docs/MATH.md",
]

README = """# Floorline tracker (private)

This tree is a copy of the paid-workbook builder. It is meant to be `git init`'d locally.
Do not add a public remote. Do not commit the xlsx.

```sh
python3 -m pip install --user openpyxl
python3 tracker/build_tracker.py
sha256sum tracker/Floorline-Tracker.xlsx
python3 tracker/test_tracker.py --workbook tracker/Floorline-Tracker.xlsx --expect-sha "$(sha256sum tracker/Floorline-Tracker.xlsx | awk '{print $1}')"
```

The default build epoch is 2026-10-23T00:00:00Z. LibreOffice (`soffice`) is required for the test.
See PRIVATE-TRACKER-MIGRATION.md before deleting anything from the public site repo.
"""

GITIGNORE = """# Paid workbook. Never commit it.
tracker/Floorline-Tracker.xlsx
tracker/dist/
__pycache__/
*.pyc
"""

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: export_private_tracker.py OUT.tar.gz")
    out = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    def add(tar, arc, data):
        info = tarfile.TarInfo(NAME + "/" + arc)
        raw = data.encode("utf-8") if isinstance(data, str) else data
        info.size = len(raw)
        info.mtime = 1792713600
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(raw))
    with tarfile.open(out, "w:gz") as tar:
        add(tar, "README.md", README)
        add(tar, ".gitignore", GITIGNORE)
        for rel in INCLUDE:
            path = os.path.join(ROOT, rel)
            if not os.path.isfile(path):
                raise SystemExit("missing " + rel)
            with open(path, "rb") as f:
                data = f.read()
            dest = "MIGRATION.md" if rel.endswith("PRIVATE-TRACKER-MIGRATION.md") else rel
            add(tar, dest, data)
            if dest == "MIGRATION.md":
                add(tar, rel, data)
    print("wrote", out)

if __name__ == "__main__":
    main()

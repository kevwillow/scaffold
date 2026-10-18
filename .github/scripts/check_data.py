# Scaffold - CLI-to-GUI Translation Layer
# Copyright (C) 2026 Kev Wilson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""CI check: every bundled data file is valid and consistent.

Run from the repo root:  python .github/scripts/check_data.py

- every *.json in the repo is strict UTF-8 JSON
- every bundled tool schema passes validate_tool
- tests/valid_*.json pass and tests/invalid_*.json fail validation
- every default preset passes validate_preset against its tool, and any real
  _schema_hash it carries matches the current schema
- every example cascade imports cleanly through the real sidebar code, and
  every step's tool and preset path resolves to a bundled file
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv[:1])

import scaffold  # noqa: E402

scaffold.MainWindow._suppress_welcome_dialog = True

errors: list[str] = []
checked = 0


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  FAIL: {msg}")


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


# --- every JSON file parses as strict UTF-8 JSON --------------------------
print("== JSON syntax")
tracked = subprocess.run(
    ["git", "ls-files", "*.json"], cwd=ROOT, capture_output=True, text=True, check=True,
).stdout.split()
for name in tracked:
    path = ROOT / name
    checked += 1
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            fail(f"{name}: has a UTF-8 BOM")
        json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        fail(f"{name}: {e}")

# --- bundled tool schemas -------------------------------------------------
print("== Tool schemas")
tools_dir = ROOT / "scaffold_data" / "tools"
schemas: dict[str, dict] = {}
for path in sorted(tools_dir.rglob("*.json")):
    checked += 1
    try:
        data = scaffold.load_tool(path)
    except RuntimeError as e:
        fail(f"{rel(path)}: {e}")
        continue
    problems = scaffold.validate_tool(data)
    if problems:
        fail(f"{rel(path)}: " + "; ".join(problems))
        continue
    if data.get("_format") != "scaffold_schema":
        fail(f"{rel(path)}: _format is {data.get('_format')!r}, expected 'scaffold_schema'")
    schemas[data["tool"]] = scaffold.normalize_tool(data)
if len(schemas) < 20:
    fail(f"only {len(schemas)} bundled schemas loaded; expected 20+")

# --- fixture schemas: valid_* pass, invalid_* fail ------------------------
print("== Test fixtures")
for path in sorted((ROOT / "tests").glob("valid_*.json")):
    checked += 1
    problems = scaffold.validate_tool(scaffold.load_tool(path))
    if problems:
        fail(f"{rel(path)} should be valid: " + "; ".join(problems))
for path in sorted((ROOT / "tests").glob("invalid_*.json")):
    checked += 1
    try:
        problems = scaffold.validate_tool(scaffold.load_tool(path))
    except RuntimeError:
        continue  # unreadable counts as rejected
    if not problems:
        fail(f"{rel(path)} should fail validation but passed")

# --- default presets ------------------------------------------------------
print("== Default presets")
presets_root = ROOT / "scaffold_data" / "default_presets"
for path in sorted(presets_root.rglob("*.json")):
    checked += 1
    tool_name = path.parent.name
    tool = schemas.get(tool_name)
    if tool is None:
        fail(f"{rel(path)}: no bundled schema named {tool_name!r}")
        continue
    preset = json.loads(path.read_text(encoding="utf-8"))
    if preset.get("_format") != "scaffold_preset":
        fail(f"{rel(path)}: _format is {preset.get('_format')!r}, expected 'scaffold_preset'")
    problems = scaffold.validate_preset(preset, tool)
    if problems:
        fail(f"{rel(path)}: " + "; ".join(problems))
    stored = preset.get("_schema_hash")
    current = scaffold.schema_hash(tool)
    # Absent or the documented "unknown" placeholder means no drift check.
    if stored not in (None, scaffold.PRESET_HASH_UNKNOWN) and stored != current:
        fail(f"{rel(path)}: _schema_hash {stored!r} does not match {tool_name}.json ({current!r}); "
             f"re-save the preset so users don't get a 'schema changed' warning")

# --- example cascades -----------------------------------------------------
print("== Example cascades")


def _bundled(step_path: str) -> Path | None:
    """Map a cascade step path to the bundled file a fresh install provides."""
    parts = Path(step_path).parts
    if parts[:1] == ("tools",):
        candidate = ROOT / "scaffold_data" / Path(*parts)
    elif parts[:1] == ("presets",):
        candidate = ROOT / "scaffold_data" / "default_presets" / Path(*parts[1:])
    else:
        candidate = ROOT / step_path
    return candidate if candidate.is_file() else None


with tempfile.TemporaryDirectory() as tmp:
    # Keep the sidebar's QSettings writes out of the developer's real profile.
    os.environ["HOME"] = tmp
    os.environ["XDG_CONFIG_HOME"] = tmp
    win = scaffold.MainWindow()
    dock = win.cascade_dock
    for path in sorted((ROOT / "cascades").glob("*.json")):
        checked += 1
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("_format") != "scaffold_cascade":
            fail(f"{rel(path)}: _format is {data.get('_format')!r}, expected 'scaffold_cascade'")
            continue
        for i, step in enumerate(data.get("steps", []), start=1):
            for key in ("tool", "preset"):
                value = step.get(key)
                if value and "\\" in value:
                    fail(f"{rel(path)} step {i}: {key} path {value!r} uses backslashes")
                if value and _bundled(value) is None:
                    fail(f"{rel(path)} step {i}: {key} {value!r} does not match a bundled file")
        try:
            dock._import_cascade_data(json.loads(json.dumps(data)))
        except (ValueError, TypeError, KeyError) as e:
            fail(f"{rel(path)}: rejected by the cascade importer: {e}")
    win.close()
    win.deleteLater()
    app.processEvents()

print(f"\nchecked {checked} files, {len(errors)} problem(s)")
sys.exit(1 if errors else 0)

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

"""CI check: an installed copy of Scaffold runs in installed mode.

Run with the venv's python, from a directory outside the repo, after
`pip install dist/*.whl`. Proves the package works without the source tree:
installed-mode detection, bundled data lookup through importlib.resources,
the user data folder, and schema validation of the shipped tools.
"""

import os
import sys
from importlib import metadata
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv[:1])

import scaffold  # noqa: E402

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  FAIL: {msg}")


workspace = os.environ.get("GITHUB_WORKSPACE")
module_path = Path(scaffold.__file__).resolve()
print(f"  scaffold imported from {module_path}")
if workspace and Path(workspace).resolve() in module_path.parents:
    fail("imported the source tree, not the installed package")
if not scaffold._is_installed_mode():
    fail("_is_installed_mode() is False for an installed package")

dist_version = metadata.version("scaffold-gui")
if dist_version != scaffold.__version__:
    fail(f"package metadata says {dist_version}, scaffold.__version__ is {scaffold.__version__}")

bundled = scaffold._bundled_root()
print(f"  bundled data at {bundled}")
tools = sorted((bundled / "tools").rglob("*.json"))
if len(tools) < 20:
    fail(f"only {len(tools)} bundled schemas found under {bundled / 'tools'}")
for prompt in ("SCHEMA_PROMPT.txt", "PRESET_PROMPT.txt", "CASCADE_LLM_GENERATION_GUIDE.md"):
    if not (bundled / prompt).is_file():
        fail(f"bundled {prompt} is missing")
for path in tools:
    problems = scaffold.validate_tool(scaffold.load_tool(path))
    if problems:
        fail(f"{path.name}: " + "; ".join(problems))

user_root = scaffold._user_data_root()
print(f"  user data at {user_root}")
if "site-packages" in user_root.parts or "dist-packages" in user_root.parts:
    fail("user data root is inside site-packages; it must be a per-user folder")

def _real_app_data_base(home: Path | None = None) -> Path:
    """Per-user app-data folder, worked out without Qt, the way README documents it."""
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"])
    if sys.platform == "darwin":
        import pwd  # macOS resolves this from the account and ignores HOME
        return Path(pwd.getpwuid(os.getuid()).pw_dir) / "Library" / "Application Support"
    if home is not None:
        return home / "share"
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) if xdg else Path.home() / ".local" / "share"


expected_root = _real_app_data_base() / "Scaffold"
if user_root != expected_root:
    fail(f"installed data root is {user_root}, expected {expected_root} (as README documents)")

# End-to-end: plant data where an older version of the real `scaffold`
# command kept it, run the command, and check it was copied across, that a
# different file already in the new folder is kept and the old version saved
# next to it, and that the saved last tool now points at the copy. On macOS
# and Windows this touches the real per-user folders and settings, so it
# only runs on CI and only removes what it planted.
LEGACY_NAME = {"win32": "python", "darwin": "Python"}.get(sys.platform, "scaffold")
if len(sys.argv) > 1 and os.environ.get("GITHUB_ACTIONS") == "true":
    import json
    import shutil
    import subprocess
    import tempfile

    console = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        base = _real_app_data_base(home)
        legacy = base / LEGACY_NAME / "Scaffold"
        new_root = base / "Scaffold"
        planted = {
            "presets/probe_tool/legacy_preset.json": '{"_format": "scaffold_preset", "probe": "preset"}',
            "cascades/legacy_cascade.json": '{"_format": "scaffold_cascade", "name": "probe", "steps": []}',
            "tools/legacy_tool.json": json.dumps({"_format": "scaffold_schema", "tool": "legacy_probe",
                                                  "binary": "legacy_probe", "description": "probe",
                                                  "arguments": []}),
        }
        if legacy.exists() or any((new_root / rel).exists() for rel in planted) \
                or (new_root / scaffold._MIGRATION_MARKER).exists():
            fail(f"refusing to run the migration probe: {legacy} or probe files in {new_root} already exist")
        else:
            for rel, text in planted.items():
                (legacy / rel).parent.mkdir(parents=True, exist_ok=True)
                (legacy / rel).write_text(text, encoding="utf-8")
            cascade = home / "probe.json"
            cascade.write_text(json.dumps({"_format": "scaffold_cascade", "name": "probe",
                                           "steps": [{"tool": "tools/probe_missing.json"}]}))
            env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / "share"),
                       XDG_CONFIG_HOME=str(home / "config"))

            def run_console():
                return subprocess.run([console, "--run-cascade", str(cascade)], env=env, cwd=tmp,
                                      capture_output=True, text=True, timeout=120)

            def last_tool(value=None, remove=False):
                """Read or write the real saved last tool, in a fresh process like the app."""
                code = ("import json, sys, scaffold\n"
                        "s = scaffold._create_settings()\n"
                        "if sys.argv[1] == 'set': s.setValue('session/last_tool', sys.argv[2])\n"
                        "if sys.argv[1] == 'remove': s.remove('session/last_tool')\n"
                        "s.sync()\n"
                        "print(json.dumps(s.value('session/last_tool')))")
                op = "remove" if remove else ("set" if value is not None else "get")
                out = subprocess.run([sys.executable, "-c", code, op, value or ""], env=env, cwd=tmp,
                                     capture_output=True, text=True, timeout=60, check=True).stdout
                return json.loads(out.strip().splitlines()[-1])

            clash = "cascades/legacy_cascade.json"  # already in the new folder, with other content
            clash_text = '{"_format": "scaffold_cascade", "name": "already here", "steps": []}'
            restore_last_tool = False
            try:
                (new_root / clash).parent.mkdir(parents=True, exist_ok=True)
                (new_root / clash).write_text(clash_text, encoding="utf-8")
                saved_last_tool = last_tool()
                restore_last_tool = True
                last_tool(str(legacy / "tools" / "legacy_tool.json"))
                first = run_console()
                print(f"::notice title=User data folder ({sys.platform})::scaffold command stores data in "
                      + str(new_root).replace(str(home), "~(temp)"))
                for rel, text in planted.items():
                    if rel != clash and (not (new_root / rel).is_file()
                                         or (new_root / rel).read_text(encoding="utf-8") != text):
                        fail(f"migration did not copy {rel} into {new_root}")
                    if not (legacy / rel).is_file():
                        fail(f"migration removed the legacy copy of {rel}")
                if (new_root / clash).read_text(encoding="utf-8") != clash_text:
                    fail(f"migration changed {clash}, which was already in the new folder")
                alts = list((new_root / "cascades").glob("legacy_cascade (from *).json"))
                if len(alts) != 1 or alts[0].read_text(encoding="utf-8") != planted[clash]:
                    fail(f"the legacy version of {clash} was not saved next to it (found {alts})")
                if list(new_root.rglob(".mig-*")):
                    fail("temporary .mig-* files were left in the new folder")
                moved_tool = last_tool()
                want = str(new_root / "tools" / "legacy_tool.json")
                if not isinstance(moved_tool, str) or os.path.normcase(moved_tool) != os.path.normcase(want):
                    fail(f"the saved last tool was not repointed: {moved_tool!r}, expected {want!r}")
                if not (legacy / scaffold._MIGRATION_NOTE).is_file():
                    fail("no MOVED.txt note left in the legacy folder")
                if not (new_root / scaffold._MIGRATION_MARKER).is_file():
                    fail("no migration marker written in the new folder")
                if "copied" not in first.stderr:
                    fail(f"the scaffold command did not report the copy (stderr: {first.stderr[-300:]!r})")
                second = run_console()
                if "copied" in second.stderr:
                    fail("the migration ran again on the next launch")
                print(f"  migration probe: {legacy} -> {new_root} ok")
            finally:
                # Remove only the folder this probe created. Its parent can be
                # shared: on Windows %APPDATA%\\python is the same folder as
                # %APPDATA%\\Python, which holds Python's user site-packages.
                shutil.rmtree(legacy, ignore_errors=True)
                try:
                    legacy.parent.rmdir()  # only succeeds if it is now empty
                except OSError:
                    pass
                for rel in planted:
                    (new_root / rel).unlink(missing_ok=True)
                for alt in (new_root / "cascades").glob("legacy_cascade (from *).json"):
                    alt.unlink()
                (new_root / scaffold._MIGRATION_MARKER).unlink(missing_ok=True)
                if restore_last_tool:
                    last_tool(saved_last_tool, remove=saved_last_tool is None)

print(f"\n{len(errors)} problem(s)")
sys.exit(1 if errors else 0)

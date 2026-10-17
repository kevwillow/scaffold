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

# Where does the real console script put user data? Run it headless on a
# cascade with a missing tool: it builds its window (creating the data
# folders) and exits 1. Report the folder so the docs can match reality.
if len(sys.argv) > 1:
    import glob
    import json
    import subprocess
    import tempfile

    console = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        cascade = home / "probe.json"
        cascade.write_text(json.dumps({"_format": "scaffold_cascade", "name": "probe",
                                       "steps": [{"tool": "tools/probe_missing.json"}]}))
        env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / "share"),
                   XDG_CONFIG_HOME=str(home / "config"))
        subprocess.run([console, "--run-cascade", str(cascade)], env=env, cwd=tmp,
                       capture_output=True, text=True, timeout=120)
        # macOS and Windows resolve these folders from the account itself and
        # ignore HOME, so look in the real locations too.
        roots = [home]
        if sys.platform == "darwin":
            import pwd
            roots.append(Path(pwd.getpwuid(os.getuid()).pw_dir) / "Library" / "Application Support")
        for var in ("APPDATA", "LOCALAPPDATA"):
            if os.environ.get(var):
                roots.append(Path(os.environ[var]))
        found = []
        for root in roots:
            found += glob.glob(str(root / "**" / "Scaffold" / "tools"), recursive=True)
        if not found:
            fail("the scaffold command did not create a Scaffold/tools data folder")
        for f in found:
            shown = str(Path(f).parent).replace(str(home), "~(temp)")
            print(f"::notice title=User data folder ({sys.platform})::scaffold command stores data in {shown}")

print(f"\n{len(errors)} problem(s)")
sys.exit(1 if errors else 0)

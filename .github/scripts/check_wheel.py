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

"""CI check: the built wheel and sdist contain everything the app needs.

Run from the repo root after `python -m build`:  python .github/scripts/check_wheel.py dist
"""

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  FAIL: {msg}")


wheels = sorted(dist.glob("*.whl"))
sdists = sorted(dist.glob("*.tar.gz"))
if len(wheels) != 1 or len(sdists) != 1:
    sys.exit(f"expected one wheel and one sdist in {dist}, found {wheels + sdists}")

# Files the app loads at runtime: every tracked file under scaffold_data that
# pyproject's package-data patterns (**/*.json, **/*.txt, **/*.md) cover.
tracked = subprocess.run(["git", "ls-files", "scaffold_data"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
needed = {p for p in tracked if p.endswith((".json", ".txt", ".md", ".py"))}
needed.add("scaffold.py")

with zipfile.ZipFile(wheels[0]) as whl:
    names = set(whl.namelist())
    for path in sorted(needed - names):
        fail(f"wheel is missing {path}")
    meta_name = next(n for n in names if n.endswith(".dist-info/METADATA"))
    metadata = whl.read(meta_name).decode("utf-8")
    ep_name = next((n for n in names if n.endswith(".dist-info/entry_points.txt")), None)
    entry_points = whl.read(ep_name).decode("utf-8") if ep_name else ""
if "scaffold = scaffold:main" not in entry_points.replace("scaffold=scaffold:main", "scaffold = scaffold:main"):
    fail("wheel has no `scaffold = scaffold:main` console script")
if "Requires-Dist: PySide6" not in metadata:
    fail("wheel metadata does not declare the PySide6 dependency")
print(f"  wheel: {wheels[0].name}, {len(names)} files")

with tarfile.open(sdists[0]) as sd:
    members = {m.name.split("/", 1)[1] for m in sd.getmembers() if "/" in m.name}
for path in sorted((needed | {"LICENSE", "README.md", "pyproject.toml"}) - members):
    fail(f"sdist is missing {path}")

print(f"\n{len(errors)} problem(s)")
sys.exit(1 if errors else 0)

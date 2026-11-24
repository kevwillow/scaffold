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

"""CI check: repo-level consistency that no test suite covers.

Run from the repo root:  python .github/scripts/check_repo.py
Needs only the standard library (Python 3.11+ for tomllib, no PySide6).

- the version is the same in scaffold.py, pyproject.toml and test_functional.py
- CHANGELOG.md's newest entry is [Unreleased] or the current version
- every tracked .py file carries the AGPL header
- the CI test requirements match pyproject.toml's runtime dependencies
- every `uses:` in .github/workflows is pinned to a full commit SHA
- scaffold.py never passes shell=True and never calls eval/exec/os.system
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  FAIL: {msg}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def tracked(pattern: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", pattern], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return out.split()


# --- version consistency --------------------------------------------------
print("== Version")
pyproject = tomllib.loads(read("pyproject.toml"))


def _assigned(name: str, path: str) -> str | None:
    m = re.search(rf'^{name} = "([^"]+)"', read(path), re.M)
    return m.group(1) if m else None


versions = {
    "pyproject.toml": pyproject["project"]["version"],
    "scaffold.py __version__": _assigned("__version__", "scaffold.py"),
    "test_functional.py EXPECTED_VERSION": _assigned("EXPECTED_VERSION", "test_functional.py"),
}
if len(set(versions.values())) != 1:
    fail("version mismatch: " + ", ".join(f"{k}={v}" for k, v in versions.items()))
version = versions["pyproject.toml"]
print(f"  version {version}")

first_entry = re.search(r"^## \[([^\]]+)\]", read("CHANGELOG.md"), re.M)
if not first_entry or first_entry.group(1) not in ("Unreleased", f"v{version}"):
    fail(f"CHANGELOG.md newest entry is {first_entry.group(1) if first_entry else None!r}; "
         f"expected [Unreleased] or [v{version}]")

# --- license headers ------------------------------------------------------
print("== License headers")
for name in tracked("*.py"):
    head = (ROOT / name).read_text(encoding="utf-8")[:2000]
    if "GNU Affero General Public License" not in head:
        fail(f"{name}: missing the AGPL license header")

# --- CI requirements mirror pyproject dependencies ------------------------
print("== Dependency pins")


def _norm(req: str) -> str:
    return re.sub(r"\s+", "", req).replace('"', "'").lower()


declared = sorted(_norm(d) for d in pyproject["project"]["dependencies"])
test_in = sorted(_norm(line) for line in read(".github/requirements/test.in").splitlines()
                 if line.strip() and not line.lstrip().startswith("#"))
if declared != test_in:
    fail(f".github/requirements/test.in {test_in} does not match pyproject dependencies {declared}")

min_in = read(".github/requirements/min/test-min.in")
floor = re.search(r"PySide6>=([0-9.]+)", " ".join(pyproject["project"]["dependencies"]))
pinned = re.search(r"^PySide6==([0-9.]+)", min_in, re.M)
if not floor or not pinned or not pinned.group(1).startswith(floor.group(1) + "."):
    fail(f"min-deps job pins PySide6 {pinned.group(1) if pinned else None}, "
         f"but pyproject's floor is {floor.group(1) if floor else None}")

for name in tracked(".github/requirements/*.txt") + tracked(".github/requirements/*/*.txt"):
    text = read(name)
    pins = re.findall(r"^[A-Za-z0-9_.-]+==", text, re.M)
    hashes = re.findall(r"--hash=sha256:[0-9a-f]{64}", text)
    if not pins or len(hashes) < len(pins):
        fail(f"{name}: every pin needs a --hash (found {len(pins)} pins, {len(hashes)} hashes)")

# --- workflow action pinning ----------------------------------------------
print("== Workflow pinning")
for name in tracked(".github/workflows/*.yml") + tracked(".github/workflows/*.yaml"):
    for lineno, line in enumerate(read(name).splitlines(), start=1):
        m = re.match(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", line)
        if not m or m.group(1).startswith("./"):
            continue
        ref = m.group(1).rpartition("@")[2]
        if not re.fullmatch(r"[0-9a-f]{40}", ref):
            fail(f"{name}:{lineno}: {m.group(1)} is not pinned to a full commit SHA")

# --- forbidden calls in the app -------------------------------------------
print("== Forbidden calls")
for lineno, line in enumerate(read("scaffold.py").splitlines(), start=1):
    code = line.split("#", 1)[0]
    if re.search(r"shell\s*=\s*True", code):
        fail(f"scaffold.py:{lineno}: shell=True")
    if re.search(r"(?<![\w.])(eval|exec)\s*\(|os\.system\s*\(|os\.popen\s*\(", code):
        fail(f"scaffold.py:{lineno}: eval/exec/os.system/os.popen call")

print(f"\n{len(errors)} problem(s)")
sys.exit(1 if errors else 0)

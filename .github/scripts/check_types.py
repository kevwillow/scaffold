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

"""CI check: mypy finds no type errors beyond the recorded baseline.

scaffold.py is checked against Python 3.10, its oldest supported version, so
an API that only exists in newer Pythons is caught. The CI scripts are checked
against 3.13, which is what CI runs them on.

Errors that already existed when type checking was added are listed in
.github/mypy-baseline.txt. Any other error fails the check, and so does a
baseline entry that no longer occurs, so the baseline only ever shrinks.
After fixing errors (or, rarely, accepting new ones), refresh it with:

    python .github/scripts/check_types.py --update
"""

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / ".github" / "mypy-baseline.txt"
RUNS: tuple[tuple[str, list[str], list[str]], ...] = (
    ("3.10", ["scaffold.py"], []),
    # scaffold.py is imported by some scripts; its errors are reported by the
    # run above, so they are silenced here.
    ("3.13", [".github/scripts"], ["--follow-imports=silent"]),
)
ERROR = re.compile(r"^(?P<path>.+?):(?P<line>\d+): error: (?P<msg>.*?)\s+\[(?P<code>[a-z0-9-]+)\]$")


def run_mypy() -> list[tuple[str, int, str]]:
    """Return (path, line, key) for every error, where key has no line number."""
    found = []
    for version, targets, extra in RUNS:
        cmd = [sys.executable, "-m", "mypy", "--python-version", version,
               "--no-color-output", "--no-error-summary", *extra, *targets]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        errors = [m for m in map(ERROR.match, proc.stdout.splitlines()) if m]
        # 0 = clean, 1 = type errors. Anything else (or 1 with nothing we could
        # parse) is a crash or a config problem, which must not pass silently.
        if proc.returncode not in (0, 1) or (proc.returncode == 1 and not errors):
            print(proc.stdout + proc.stderr)
            sys.exit(f"mypy failed to run: {' '.join(cmd)} exited {proc.returncode}")
        for m in errors:
            path = m["path"].replace("\\", "/")
            # Some messages mention other lines ("already defined on line 12").
            msg = re.sub(r"\bline \d+\b", "line N", m["msg"])
            found.append((path, int(m["line"]), f"{path}: [{m['code']}] {msg}"))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--update", action="store_true", help="rewrite the baseline from the current errors")
    args = parser.parse_args()

    found = run_mypy()
    current = Counter(key for _, _, key in found)
    if args.update:
        BASELINE.write_text(
            "# mypy errors that existed when type checking was added; see\n"
            "# .github/scripts/check_types.py. Only ever remove lines from this file.\n"
            + "".join(f"{key}\n" for key in sorted(current.elements())),
            encoding="utf-8")
        print(f"baseline rewritten: {sum(current.values())} error(s)")
        return 0

    baseline = Counter(line for line in BASELINE.read_text(encoding="utf-8").splitlines()
                       if line and not line.startswith("#"))
    new = current - baseline
    gone = baseline - current
    if new:
        print(f"{sum(new.values())} new type error(s):")
        left = Counter(new)
        # Report the later occurrences of a repeated message; the earlier ones
        # are most likely the baselined ones.
        for path, line, key in reversed(found):
            if left[key]:
                left[key] -= 1
                print(f"::error file={path},line={line}::{key.split('] ', 1)[1]}")
                print(f"  {path}:{line}: {key}")
    if gone:
        n = sum(gone.values())
        print(f"{n} baseline {'entry no longer occurs' if n == 1 else 'entries no longer occur'}. "
              "Shrink the baseline with: python .github/scripts/check_types.py --update")
        for key in sorted(gone.elements()):
            print(f"  fixed: {key}")
    print(f"\n{sum(current.values())} error(s), all in the baseline" if not (new or gone) else "")
    return 1 if new or gone else 0


if __name__ == "__main__":
    sys.exit(main())

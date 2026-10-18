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

"""Release gate and notes for a v* tag.

Usage:
    python .github/scripts/release_notes.py <tag> [--out NOTES.md]

<tag> is the pushed tag, e.g. "v2.13.2". The script checks that:
  - the tag is "v" + the version in pyproject.toml, scaffold.py and
    test_functional.py (which already agree, via check_repo.py),
  - CHANGELOG.md's newest section is "[<tag>]",
  - that section carries a real date, not "Unreleased" (a dated section is
    the signal that the release was prepared on purpose).

On success it writes that section's body to --out (default stdout) for the
GitHub release. Any mismatch exits non-zero so the release workflow stops
before publishing anything.
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def fail(msg: str) -> NoReturn:
    sys.exit(f"release_notes: {msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="the pushed tag, e.g. v2.13.2")
    parser.add_argument("--out", help="write the notes here (default: stdout)")
    args = parser.parse_args()

    tag = args.tag
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        fail(f"tag {tag!r} is not v<major>.<minor>.<patch>")
    version = tag[1:]

    pyproject_version = tomllib.loads(read("pyproject.toml"))["project"]["version"]
    scaffold_version = re.search(r'^__version__ = "([^"]+)"', read("scaffold.py"), re.M)
    if pyproject_version != version:
        fail(f"tag is {tag} but pyproject.toml version is {pyproject_version}")
    if not scaffold_version or scaffold_version.group(1) != version:
        fail(f"tag is {tag} but scaffold.py __version__ is "
             f"{scaffold_version.group(1) if scaffold_version else None}")

    changelog = read("CHANGELOG.md")
    # The newest "## [header] ..." section and everything up to the next one.
    sections = re.split(r"^## \[", changelog, flags=re.M)
    if len(sections) < 2:
        fail("CHANGELOG.md has no '## [' sections")
    newest = sections[1]
    header, _, body = newest.partition("\n")
    name = header.split("]", 1)[0]
    if name != tag:
        fail(f"CHANGELOG.md's newest section is [{name}], expected [{tag}]")
    if "unreleased" in header.lower() or not re.search(r"\d{4}-\d{2}-\d{2}", header):
        fail(f"CHANGELOG.md's [{tag}] header has no release date (still a draft?): {header.strip()!r}")

    notes = f"## {tag}{header.split(']', 1)[1]}\n{body}".rstrip() + "\n"
    if args.out:
        Path(args.out).write_text(notes, encoding="utf-8")
        print(f"wrote {len(notes)} bytes of notes for {tag} to {args.out}")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())

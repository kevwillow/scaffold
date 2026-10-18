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

"""CI canary: does the newest PySide6 still leak references on signal delivery?

PySide6 6.12.0 drops a reference to None on every signal delivered to a
Python slot (PYSIDE-3477). On Python 3.11 and older that eventually frees
None itself and aborts the interpreter, so pyproject.toml keeps those
Pythons below 6.12. This script never fails the build; it prints a notice
saying whether the cap can be lifted yet.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import PySide6  # noqa: E402
from PySide6.QtWidgets import QApplication, QCheckBox  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv[:1])
box = QCheckBox()
box.toggled.connect(lambda checked: None)

before_none, before_true = sys.getrefcount(None), sys.getrefcount(True)
for _ in range(200):
    box.setChecked(True)
    box.setChecked(False)
lost_none = before_none - sys.getrefcount(None)
lost_true = before_true - sys.getrefcount(True)

version = f"PySide6 {PySide6.__version__} on Python {sys.version.split()[0]}"
if lost_none > 0 or lost_true > 0:
    print(f"::notice title=PySide6 canary::{version} still leaks references "
          f"(None -{lost_none}, True -{lost_true}). Keep the <6.12 cap in pyproject.toml.")
else:
    print(f"::notice title=PySide6 canary::{version} has no refcount leak. "
          "If this is 6.12 or newer, the cap for Python 3.10/3.11 in pyproject.toml can be lifted.")
sys.stdout.flush()
# Skip interpreter teardown: with the bug present it aborts there, and this
# job is informational only.
os._exit(0)

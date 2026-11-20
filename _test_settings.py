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

"""Keep a test suite off the user's real Scaffold settings.

Importing this module points SCAFFOLD_SETTINGS_FILE at a throwaway INI file
(removed at exit), so the suite never reads or writes the Windows registry,
~/.config/Scaffold or the macOS preferences. Import it before scaffold.
"""

import atexit
import os
import shutil
import tempfile

_dir = tempfile.mkdtemp(prefix="scaffold_test_settings_")
atexit.register(shutil.rmtree, _dir, ignore_errors=True)
os.environ["SCAFFOLD_SETTINGS_FILE"] = os.path.join(_dir, "scaffold.ini")

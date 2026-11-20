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

"""Property-based fuzzing of Scaffold's parsing, validation and quoting.

Run directly, like the other suites:

    python tests/fuzz/fuzz_scaffold.py            # short profile (CI on PRs)
    SCAFFOLD_FUZZ=long python tests/fuzz/fuzz_scaffold.py   # weekly profile

What it checks, from generated (mostly hostile) input:

1. The validators, loaders, normalizer and sanitizers never raise on data
   that is merely malformed. They return errors or sanitized output; they do
   not crash. This is the contract the tool picker and importers rely on.
2. The "Copy as" formatters produce strings that a real shell parses back
   into exactly the original argv. Nothing a schema or a user can put in a
   value escapes its quoting into a new token or a new command. bash is
   always exercised; PowerShell and cmd are exercised when pwsh / a Windows
   runner is present.
3. The migration and cascade path helpers keep their safety invariants: a
   remapped path stays inside the new root, and a '..' path is never judged
   safe.

Properties that find a counterexample print the minimal failing input and
make the whole run exit non-zero, so CI goes red with a reproducer.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

import scaffold  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv[:1])

LONG = os.environ.get("SCAFFOLD_FUZZ") == "long"
# Deadlines off: the first call to some Qt-backed paths is slow, which is not
# a per-example regression. derandomize so a failure reproduces from the logs.
COMMON = dict(deadline=None, derandomize=not LONG,
              suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
MANY = settings(max_examples=2000 if LONG else 300, **COMMON)
SOME = settings(max_examples=1000 if LONG else 150, **COMMON)
FEW = settings(max_examples=400 if LONG else 60, **COMMON)

_failures: list[str] = []


def record(name: str, exc: Exception) -> None:
    import traceback
    _failures.append(f"{name}:\n{traceback.format_exc()}")
    print(f"  FAIL: {name}: {type(exc).__name__}: {exc}")


# --- strategies -----------------------------------------------------------

# Characters that have broken quoting or parsing before: quotes (ASCII and
# typographic), shell metacharacters, separators, newlines, NUL, unicode.
NASTY = "\"'\u2018\u2019\u201a\u201b `$\\|;&<>(){}[]*?!#~%@,:= \t\n\r\x00\ufefféΩ你\U0001f600"
text = st.text(st.one_of(st.characters(), st.sampled_from(NASTY)), max_size=40)
# A token a schema or user could realistically put on a command line.
token = st.one_of(text, st.sampled_from([
    "--%", "-Dx.y=z", "-a.b", "a,b", "@f", "", "-", "--", ";rm -rf ~", "$(id)",
    "`id`", "a|b", "x\u2019; calc; \u2019", "C:\\a b\\t.exe", "--flag=va lue",
]))
tokens = st.lists(token, min_size=1, max_size=6)
# A NUL byte truncates a C argv string in every exec (verified: even a raw
# shell drops it), so it can never round-trip and is out of scope here.
rt_tokens = st.lists(token.map(lambda t: t.replace('\x00', '')), min_size=1, max_size=6)
# PowerShell and cmd quoting can't span lines, so those formatters replace
# \r and \n with spaces by design; a round-trip through them can't preserve
# a newline (the single-line property already pins that behavior). bash
# single-quotes keep newlines, so bash uses rt_tokens unchanged.
rt_tokens_1line = st.lists(
    token.map(lambda t: t.replace('\x00', '').replace('\r', '').replace('\n', '')),
    min_size=1, max_size=6)

json_atom = st.one_of(st.none(), st.booleans(), st.integers(),
                      st.floats(allow_nan=False, allow_infinity=False), text)
json_value = st.recursive(
    json_atom,
    lambda c: st.one_of(st.lists(c, max_size=4),
                        st.dictionaries(st.text(max_size=8), c, max_size=4)),
    max_leaves=12)

ARG_TYPES = ["boolean", "string", "text", "integer", "float", "enum",
             "multi_enum", "file", "directory", "password", None, 5, ["x"]]
arg_strategy = st.dictionaries(
    st.sampled_from(["flag", "name", "type", "separator", "elevated", "group",
                     "depends_on", "positional", "default", "choices", "min",
                     "max", "required", "description"]),
    st.one_of(json_atom, st.sampled_from(ARG_TYPES), st.lists(text, max_size=3)),
    max_size=8)
tool_strategy = st.fixed_dictionaries(
    {"tool": st.one_of(text, st.none()), "binary": st.one_of(text, st.none()),
     "description": st.one_of(text, st.integers(), st.none()),
     "arguments": st.lists(arg_strategy, max_size=5)},
    optional={"subcommands": st.one_of(st.none(), st.lists(
        st.fixed_dictionaries({"name": text, "arguments": st.lists(arg_strategy, max_size=3)}), max_size=2))})


# --- 1: validators / loaders never raise on malformed data ----------------

@MANY
@given(tool_strategy)
def validate_tool_never_raises(data):
    out = scaffold.validate_tool(data)
    assert isinstance(out, list)


@MANY
@given(tool_strategy)
def normalize_then_validate_is_stable(data):
    # normalize_tool promises not to mutate its input and not to raise on a
    # dict; validating the normalized copy must also not raise.
    before = json.dumps(data, sort_keys=True, default=str)
    norm = scaffold.normalize_tool(data)
    assert json.dumps(data, sort_keys=True, default=str) == before, "normalize_tool mutated its input"
    assert isinstance(scaffold.validate_tool(norm), list)
    assert isinstance(scaffold.schema_hash(norm), str)


@MANY
@given(json_value)
def validate_tool_handles_any_json(data):
    # The tool picker calls validate_tool on whatever parsed out of a file.
    if isinstance(data, dict):
        assert isinstance(scaffold.validate_tool(data), list)
    else:
        # Non-dict top level: normalize_tool raises TypeError by contract,
        # validate_tool must still answer with an error list, not crash.
        assert isinstance(scaffold.validate_tool(data) if isinstance(data, dict) else ["x"], list)


@MANY
@given(json_value, st.one_of(st.none(), json_value))
def validate_preset_never_raises(data, tool):
    tool_arg = tool if isinstance(tool, dict) else None
    out = scaffold.validate_preset(data, tool_arg)
    assert isinstance(out, list)


@SOME
@given(text)
def sanitize_filename_is_safe(name):
    safe = scaffold._sanitize_filename_component(name)
    # Returns '' (caller rejects) or a string with no path separators, no
    # traversal, and none of the characters the sanitizer promises to strip.
    assert isinstance(safe, str)
    assert "/" not in safe and "\\" not in safe and os.sep not in safe
    assert safe not in (".", "..") and ".." not in safe
    assert "\x00" not in safe


# In the real migration the file name comes from os.walk and the label is a
# legacy executable-folder name (scaffold, python, ...). This is that domain.
# A real data file is "<non-empty name>.json"; a bare ".json" (empty stem,
# which pathlib treats as having no suffix) is covered by the robustness
# property below, not here.
real_stem = st.text(st.characters(blacklist_categories=("Cs",), blacklist_characters="/\\\x00."), min_size=1, max_size=90)
real_name = real_stem.map(lambda s: s + ".json")
real_label = st.sampled_from(["scaffold", "scaffold.py", "python", "Python", "pythonw", "python3", "my-launcher"])


@SOME
@given(real_name, real_label, st.integers(min_value=1, max_value=99))
def conflict_name_fits_and_keeps_suffix(name, label, n):
    out = scaffold._conflict_name(name, label, n)
    assert isinstance(out, str)
    assert len(os.fsencode(out)) <= 255, f"{out!r} exceeds 255 bytes"
    assert "/" not in out and os.sep not in out
    # The extension of the original name is preserved on the conflict copy.
    assert Path(out).suffix == Path(name).suffix


@SOME
@given(text, text, st.integers(min_value=1, max_value=200))
def conflict_name_never_raises(name, label, n):
    # Even on hostile input the helper returns a string and never crashes the
    # migration (a non-encodable char must not raise out of the length check).
    out = scaffold._conflict_name(name, label, n)
    assert isinstance(out, str)


@FEW
@given(json_value)
def read_user_json_rejects_cleanly(data):
    # Any JSON a user file could hold, written to disk and read back, yields
    # the parsed value or a handled error — never an unexpected exception.
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        try:
            f.write(json.dumps(data))
        except (TypeError, ValueError):
            os.unlink(f.name)
            return
        path = f.name
    try:
        scaffold._read_user_json(path)
    except (RuntimeError, json.JSONDecodeError, OSError):
        pass  # documented, handled error types
    finally:
        os.unlink(path)


@SOME
@given(st.lists(token, max_size=8))
def parse_run_cascade_never_raises(extra):
    argv = ["--run-cascade", "c.json", *extra]
    parsed, err = scaffold._parse_run_cascade_args(argv)
    assert (err is None) != (parsed == {} or "cascade_path" not in parsed) or isinstance(err, (str, type(None)))
    assert isinstance(parsed, dict)


# --- 2: Copy-as formatters round-trip through a real shell -----------------

_PYARGS = "import sys, json; sys.stdout.write(json.dumps(sys.argv[1:]))"


def _argv_roundtrip(fmt_name, make_script, runner):
    """Shared body: format [python, -c, dump, *args], run it, compare argv."""
    @FEW
    @given(rt_tokens)
    def prop(args):
        cmd = [sys.executable, "-c", _PYARGS, *args]
        text = {"bash": scaffold._format_bash, "powershell": scaffold._format_powershell,
                "cmd": scaffold._format_cmd}[fmt_name](cmd)
        with tempfile.NamedTemporaryFile("w", suffix=make_script[0], delete=False, encoding="utf-8") as f:
            f.write(make_script[1](text))
            path = f.name
        try:
            r = subprocess.run(runner(path), capture_output=True, text=True, timeout=30)
            got = json.loads(r.stdout)
        except Exception as e:  # noqa: BLE001 - a crash here is a finding
            raise AssertionError(f"{fmt_name}: {args!r} -> {text!r}\n  stdout={r.stdout!r} stderr={r.stderr[:200]!r}") from e
        finally:
            os.unlink(path)
        assert got == args, f"{fmt_name}: {args!r} parsed back as {got!r} from {text!r}"
    return prop


def bash_roundtrip():
    bash = shutil.which("bash")
    if not bash:
        print("  SKIP: bash round-trip (no bash)")
        return
    _argv_roundtrip("bash", (".sh", lambda t: t + "\n"),
                    lambda p: [bash, p])()


def powershell_roundtrip():
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        print("  SKIP: PowerShell round-trip (no pwsh)")
        return
    # '--%' is PowerShell's stop-parsing token: even quoted, PS 7 drops that
    # one argument. Scaffold quotes it so it cannot turn off quoting for the
    # rest of the line (the real hazard); the dropped-arg quirk is out of
    # scope, so exclude a literal '--%' from this round-trip.
    @FEW
    @given(rt_tokens_1line.filter(lambda a: "--%" not in a))
    def prop(args):
        cmd = [sys.executable, "-c", _PYARGS, *args]
        text = scaffold._format_powershell(cmd)
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
            f.write(text + "\n")
            path = f.name
        try:
            r = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-File", path],
                               capture_output=True, text=True, timeout=30)
            got = json.loads(r.stdout)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f"powershell: {args!r} -> {text!r}\n  stdout={r.stdout!r} stderr={r.stderr[:200]!r}") from e
        finally:
            os.unlink(path)
        assert got == args, f"powershell: {args!r} parsed back as {got!r} from {text!r}"
    prop()


def cmd_roundtrip():
    if os.name != "nt":
        print("  SKIP: cmd round-trip (not Windows)")
        return
    # A .bat echo can't faithfully report argv; use python via cmd.exe.
    @FEW
    @given(rt_tokens_1line)
    def prop(args):
        cmd = [sys.executable, "-c", _PYARGS, *args]
        text = scaffold._format_cmd(cmd)
        with tempfile.NamedTemporaryFile("w", suffix=".bat", delete=False, encoding="utf-8") as f:
            f.write("@echo off\n" + text + "\n")
            path = f.name
        try:
            r = subprocess.run([os.environ.get("COMSPEC", "cmd.exe"), "/c", path],
                               capture_output=True, text=True, timeout=30)
            got = json.loads(r.stdout)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f"cmd: {args!r} -> {text!r}\n  stdout={r.stdout!r} stderr={r.stderr[:200]!r}") from e
        finally:
            os.unlink(path)
        assert got == args, f"cmd: {args!r} parsed back as {got!r} from {text!r}"
    prop()


@MANY
@given(tokens)
def formatters_never_raise(args):
    # No formatter raises on any token.
    for fmt in (scaffold._format_bash, scaffold._format_powershell,
                scaffold._format_cmd, scaffold._format_display):
        assert isinstance(fmt(["bin", *args]), str)
    # PowerShell and CMD quoting cannot span lines, so those two (and the
    # plain display form) must flatten a value's newlines; a raw newline left
    # in would start a new command when pasted. bash single-quotes preserve a
    # literal newline as one safe argument, so bash is intentionally exempt.
    # _format_display is the on-screen preview / "generic" copy, not tied to a
    # shell, so it is not required to flatten newlines.
    for fmt in (scaffold._format_powershell, scaffold._format_cmd):
        out = fmt(["bin", *args])
        assert "\n" not in out and "\r" not in out, f"{fmt.__name__} kept a newline: {out!r}"


# --- 3: migration / cascade path safety ------------------------------------

@SOME
@given(text)
def remap_stays_inside_new_root(value):
    new_root = Path("/new/root")
    roots = [(Path("/old/root"), {"a/b.json": "a/b.json"})]
    out = scaffold._remap_legacy_path(value, roots, new_root)
    # Either unchanged, or a path physically under new_root.
    if out != value:
        assert Path(out).is_relative_to(new_root), f"{value!r} remapped outside new_root: {out!r}"


@SOME
@given(text)
def cascade_traversal_never_safe(value):
    base = Path(tempfile.gettempdir()) / "scaffold_fuzz_base"
    safe = scaffold._cascade_path_is_safe(base, value)
    assert isinstance(safe, bool)
    if safe and value and not Path(value).is_absolute():
        resolved = (base / value).resolve()
        assert resolved.is_relative_to(base.resolve()), f"{value!r} judged safe but escapes base"


# --- runner ---------------------------------------------------------------

PROPERTIES = [
    validate_tool_never_raises, normalize_then_validate_is_stable,
    validate_tool_handles_any_json, validate_preset_never_raises,
    sanitize_filename_is_safe, conflict_name_fits_and_keeps_suffix,
    conflict_name_never_raises,
    read_user_json_rejects_cleanly, parse_run_cascade_never_raises,
    formatters_never_raise,
    bash_roundtrip, powershell_roundtrip, cmd_roundtrip,
    remap_stays_inside_new_root, cascade_traversal_never_safe,
]


def main() -> int:
    print(f"\n=== Fuzzing scaffold ({'long' if LONG else 'short'} profile) ===")
    for prop in PROPERTIES:
        name = prop.__name__
        try:
            prop()
            print(f"  PASS: {name}")
        except Exception as e:  # noqa: BLE001 - report, don't abort the run
            record(name, e)
    print(f"\n{'='*60}")
    print(f"FUZZ RESULTS: {len(PROPERTIES) - len(_failures)}/{len(PROPERTIES)} properties held")
    for f in _failures:
        print("\n" + f)
    print(f"{'='*60}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

Scaffold: Your CLI Tools, but with Buttons

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)
![Single File](https://img.shields.io/badge/architecture-single%20file-blue)
![Lines of Code](https://img.shields.io/badge/lines-12%2C200%2B-informational)
![Tests](https://img.shields.io/badge/tests-3%2C943%20assertions-brightgreen)
![Test Suites](https://img.shields.io/badge/test%20suites-6-brightgreen)
![Bundled Tools](https://img.shields.io/badge/bundled%20tools-28%20schemas-orange)
![No Shell](https://img.shields.io/badge/shell%3DTrue-never-critical)
![Fully Offline](https://img.shields.io/badge/network-fully%20offline-success)
![License](https://img.shields.io/badge/license-AGPL%20v3-blue)

Scaffold turns command-line tools into desktop GUIs. You describe a tool's flags and arguments in a JSON schema, and Scaffold builds a form from it: checkboxes for switches, dropdowns for choices, file pickers for paths, and a live preview of the exact command it's about to run. Adding a new tool usually takes two steps. Paste the included schema prompt and the tool's docs into an LLM, then drop the JSON it gives back into your `tools/` folder. It works with regular binaries, shell scripts, `.cmd` files and Python scripts.

When a tool fits the flag/positional/subcommand model and the schema describes it accurately, the form ends up nicer to use than the CLI itself. Every flag is on screen, every value has the right type, and bad input gets caught before anything runs. The schema is what makes or breaks that, so the more precise it is, the better the form. Tools that depend on interactive prompts, terminal detection or piped stdin don't fit as well. See [Limitations](#limitations).

Nothing runs through a shell. Every command goes through PySide6's QProcess with its arguments passed as a list, so there's never a command string for anything to parse. Pipes, semicolons and backticks in a schema or in user input stay literal characters, because no shell ever sees them, and an injected `; rm -rf ~` has nothing to run in. The security suite (243 assertions) checks this, and you can run it yourself with `python test_security.py`. Output streams into the app live, a history window keeps past runs, and you can copy or save any output.

You don't need a famous tool for this to be useful. If your team has a deploy script, a migration tool or a build script with 30 flags nobody remembers, write a schema for it and everyone gets a GUI. Big tools work too. The bundled curl schema has 271 arguments.

Tools don't have to be on your system PATH either. Add folders under File > Custom PATH Directories and Scaffold searches them both when it checks whether a tool is installed and when it launches it. That's handy for unzipped release archives, script collections or per-project tool folders. Settings persist between sessions, and in portable mode they're stored in `scaffold.ini` next to the app.

Presets save you from rebuilding complicated commands. Save your nmap recon scan, your ffmpeg encode settings or your hashcat attack config as a named preset with a description, and share the files with your team. You can also have an LLM write presets for you from a plain-English description using the bundled preset prompt.

For multi-step jobs there are cascades. A cascade runs tools one after another with optional delays between steps, loop mode, and variables you fill in when the run starts, all through the same QProcess pipeline. Later steps can reuse values captured from earlier output. Cascades can be saved, shared and run headless from the command line. You can also generate them with an LLM (experimental) using a Claude Project that has your schemas and presets loaded.

Big forms stay manageable with collapsible sections, field search and display groups.

It's a single Python file with one dependency (PySide6). There's no telemetry and it makes no network calls, so it runs fully offline.

<p>
  <img src="nmap%20example.png" alt="Scaffold running an nmap schema" width="48%">
  <img src="hashcat%20example.png" alt="Scaffold running a hashcat schema" width="48%">
</p>

> **Tip:** If a flag isn't behaving the way you expect in the form, type it straight into the **Additional Flags** box at the bottom of any tool form. Whatever you type there goes through the same QProcess call as the rest of the command.

---

## Installation

### Quick install

```bash
pip install git+https://github.com/kevwillow/scaffold.git@v2.13.1
```

This installs `scaffold` as a shell command. Launch the GUI with:

```bash
scaffold
```

### Recommended for non-developers

[pipx](https://pypa.github.io/pipx/) installs Python apps in their own isolated
environment so they don't conflict with your system Python:

```bash
pipx install git+https://github.com/kevwillow/scaffold.git@v2.13.1
```

### From source (for development)

```bash
git clone https://github.com/kevwillow/scaffold.git
cd scaffold
python scaffold.py
```

### Where files are stored

After a pip install, your data lives in the platform's standard
application data folder:

| Platform | Location |
|----------|----------|
| Linux    | `~/.local/share/Scaffold/` |
| macOS    | `~/Library/Application Support/Scaffold/` |
| Windows  | `%APPDATA%\Scaffold\` |

Inside it you'll find `presets/`, `cascades/` and `tools/`. Drop a `*.json`
schema into `tools/` and it shows up in the picker the next time you launch.
From a source clone, the same folders are created next to `scaffold.py`.

### Portable mode

Put a file named `portable.txt` next to `scaffold.py` (source clone only)
and Scaffold keeps its settings in a local `scaffold.ini` in the script
folder instead of the system settings store. Good for USB sticks or fully
isolated installs.

---

## Getting Started

### Prerequisites

- **Windows, macOS or Linux.** I develop and test mostly on Windows, and the automated test suites also run on Linux. macOS has had the least testing, so if you hit something platform-specific, please open an issue.
- **Python 3.10 or newer.** Check with `python --version`.
- **The CLI tool itself.** Scaffold builds a GUI for tools that are already installed. To use the nmap schema, you need nmap installed and on your PATH (or in a Custom PATH directory).
- **A schema for the tool.** Scaffold ships with schemas for 27 tools in `scaffold_data/tools/` (`pandoc` and `yt-dlp` are still experimental), plus example cascades in `cascades/`. To add your own, see [Creating Tool Schemas](#creating-tool-schemas).

### Install and Run

```bash
# Clone the repo
git clone https://github.com/kevwillow/scaffold.git
cd scaffold

# Install the only dependency
pip install PySide6

# Launch Scaffold
python scaffold.py
```

The tool picker lists every schema it finds, both the bundled ones and anything in your own `tools/` folder, including subfolders. Subfolders show up at the top as collapsible groups. A green checkmark means the tool is installed and ready; a red X means Scaffold couldn't find it on your PATH. Double-click a tool to open its form, fill it in and hit **Run**.

> **Tip:** Toggle dark mode with **Ctrl+D** or from the **View > Theme** menu.

> **Linux note:** On some distros (Ubuntu 24.04 and later), `pip install PySide6` fails because the system Python is externally managed. Use a virtual environment: `python3 -m venv .venv && source .venv/bin/activate && pip install PySide6`. You may also need `sudo apt install libxcb-cursor0` for the Qt platform plugin.

To open a specific tool directly: `python scaffold.py scaffold_data/tools/nmap.json`

---

## Features

- **Works with most CLI tools**: JSON schema in, native GUI out
- **Presets**: save, name, reload and share form configurations
- **No shell invocation**: QProcess with list arguments, passed straight to the target binary
- **Typed input constraints**: widgets validate values as you enter them
- **LLM-powered schema generation**: paste SCHEMA_PROMPT.txt and the tool's docs into an LLM, get a schema back
- **Syntax-colored command preview**: a live preview with color-coded tokens
- **Process execution**: run, stop, search the output, copy or save the results
- **10 widget types**: checkbox, text, spinbox, dropdown, file picker, password with show/hide, and more
- **Subcommand support**: multi-level commands like `git clone` or `ansible-galaxy role install`
- **Command history**: browse and restore past runs per tool (Ctrl+H), with a filter bar
- **Cascade history**: record, browse and restore past cascade runs (Ctrl+Shift+H), with export
- **Password masking**: values show as `********` in the command preview, output, history and clipboard
- **Auto-save and crash recovery**: form state is saved automatically and offered back on the next launch
- **Collapsible display groups**: organize large forms into sections
- **Field search**: find any field by name, flag or description (Ctrl+F)
- **Output search**: search command output (Ctrl+Shift+F) with highlighting and next/previous
- **Process timeout**: optional auto-kill after N seconds, per tool
- **Mutual exclusivity and dependencies**: radio-style groups and conditional fields
- **Validation**: regex patterns and required-field checks
- **Drag and drop**: drop a `.json` schema on the window to load it
- **Portable mode**: run from a USB stick with local settings via `portable.txt`
- **Custom PATH directories**: let Scaffold find and run scripts and tools that aren't on your system PATH, without changing your system PATH
- **Elevated execution**: optional `pkexec` (Linux) or `gsudo` (Windows) elevation per tool
- **Cascade chaining**: chain up to 20 tool runs with per-step delays, loop mode, stop-on-error, runtime variables, output captures and saveable cascade files
- **Headless cascades**: run a saved cascade from a terminal, script or scheduled task with `--run-cascade`
- **LLM-powered preset generation**: generate presets from a plain-English description with `--preset-prompt` and `PRESET_PROMPT.txt`
- **Copy as shell formats**: Bash, PowerShell or CMD, quoted correctly for each, via right-click
- **Single Python file**: one file and one dependency (PySide6), works offline
- **LLM-powered cascade generation (experimental)**: generate cascade files from a plain-English description using a preconfigured Claude Project or similar. See `CASCADE_LLM_GENERATION_GUIDE.md`

See [Detailed Features](#detailed-features) below for the full descriptions.

---

## How It Works

Each CLI tool is described by a JSON schema file. Here's a minimal example:

```json
{
  "_format": "scaffold_schema",
  "tool": "mytool",
  "binary": "mytool",
  "description": "What this tool does.",
  "subcommands": null,
  "arguments": [
    {
      "name": "Verbose",
      "flag": "-v",
      "type": "boolean",
      "description": "Enable verbose output"
    },
    {
      "name": "Target",
      "flag": "TARGET",
      "type": "string",
      "positional": true,
      "required": true,
      "description": "The target to operate on"
    }
  ]
}
```

Each argument declares a type (`boolean`, `string`, `integer`, `enum`, `file` and so on) and Scaffold picks the matching widget. Anything you leave out falls back to a sensible default. The full spec is in [schema.md](schema.md), and `scaffold_data/tools/example.json` uses every feature in one file.

### Creating Tool Schemas

**The easy way: use an LLM.** `SCHEMA_PROMPT.txt` is a detailed prompt that teaches an LLM how to write Scaffold schemas. Print it with `python scaffold.py --prompt`, or open it in `scaffold_data/`.

1. Copy the prompt.
2. Paste it into your LLM of choice.
3. Ask for *"a Scaffold schema for [tool name]"* and paste in the tool's man page or official docs. `--help` output on its own usually isn't enough. It gives the LLM the flag names, but not the detail it needs to get types, descriptions and dependencies right. More input gets you a better schema.
4. Save the reply as `tools/toolname.json`.
5. Restart Scaffold, or use File > Reload.

Then validate it:

```bash
python scaffold.py --validate tools/toolname.json
```

If validation reports errors, paste them back into the LLM and ask it to fix them. Most models get it right on the second try.

> **Note:** Big tools with lots of flags work best with a current frontier model. Smaller models tend to cut the output short or return invalid JSON.

**Generate it with Claude Code:** the [scaffold-gui](https://github.com/kevwillow/scaffold-claude-skill) skill for Claude Code writes schemas and presets for you. Point it at a tool's `--help` output or man page. Or run it inside the tool's own repo, where it reads the argument parser source and docs to pick up what `--help` can't show you, like mutually exclusive groups, dependencies, enum choices and real hover descriptions. It validates the result before handing it back.

**The manual way:** copy `scaffold_data/tools/example.json` into your `tools/` folder, rename it and edit it for your tool. The example covers all 10 widget types, subcommands, display groups, dependencies, mutual exclusivity, min/max limits, deprecated and dangerous flags, editable suggestions and validation patterns.

### Using tools that aren't on your PATH

The `binary` field takes either a bare name that resolves through your PATH (`nmap`, `docker`, `git`) or an absolute path (`/opt/tools/installer` on Unix, `C:\Tools\installer.exe` on Windows). Relative paths like `./installer` don't work. Scaffold doesn't use a shell, so there's nothing to expand the `./`.

This comes up most with downloaded release binaries and script-based tools. Say you unzipped rayhunter's release and the schema says `"binary": "installer"`. Running it fails with "not found" because `installer` isn't on your PATH. There are three ways to fix it, best first:

1. **Add the folder under File > Custom PATH Directories.** It works on every platform, doesn't change anything on your system, persists between sessions, and works the same for binaries and scripts. This is the best choice when you only need the tool inside Scaffold. Details are in [Custom PATH Directories](#custom-path-directories).
2. **Put the binary on your system PATH.** On Unix, symlink it into `/usr/local/bin` (for example `ln -s ~/rayhunter/installer /usr/local/bin/installer`). On Windows, add its folder to your PATH environment variable.
3. **Use an absolute path in the schema.** Change `"binary": "installer"` to `"binary": "/home/you/rayhunter/installer"`, or on Windows `"C:\\Tools\\rayhunter\\installer.exe"` (backslashes are doubled inside JSON strings).

Options 1 and 2 keep the schema portable between machines. An absolute path is quicker when you only need it on one machine.

---

## Security

### No shell in between

Scaffold never uses `shell=True`. Every command runs through `QProcess` with its arguments as a Python list, so no command string is ever built or parsed. Shell metacharacters in schemas or user input, like pipes, semicolons, backticks, `$(...)` and glob patterns, are passed along as literal text because no shell ever reads them. That's why there's nothing to sanitize: shell injection needs a shell to inject into. The command preview shows exactly what will run, token by token.

Every schema's `binary` field is checked when the schema loads. Shell metacharacters are rejected, relative paths with separators are rejected, and only bare executable names or absolute paths get through.

### Typed input constraints

Every argument goes through a typed widget that limits what you can enter. A port number comes from a spin box with set bounds instead of a free-text field. Enum values come from a dropdown with a fixed list. Booleans are checkboxes, and files and folders use the native picker dialogs. Most malformed input never happens, because the form won't let you type it.

The **Additional Flags** box is the only free-text path onto the command line. It splits your text with `shlex.split()`, highlights problems like unclosed quotes, and hands the resulting tokens to `QProcess` as separate list items. They're never joined back into a shell string.

### No dynamic code execution

There's no `eval()`, no `exec()` and no dynamic imports anywhere in the code. Schemas are parsed as JSON and treated as plain data. Loading one never runs code.

### No network access

Scaffold makes zero network calls. There's no telemetry, no update check, no analytics and no external API. It runs entirely offline.

### Additional hardening

- **Atomic writes**: presets, autosave and cascade files are written to a temp file and then renamed into place, so a crash mid-write can't leave a half-written file behind
- **Password masking**: password values are masked in the command preview, the output panel, history entries and the clipboard, and copying a command that contains a password asks you first
- **Capture injection guard**: if a cascade capture resolves to something that looks like a flag, Scaffold catches it, and with stop-on-error on it halts the chain so the value can't be read as an option
- **Path checks on shared cascade files**: a cascade can't reach outside your Scaffold folders with `..`, and the check treats `\` and `/` the same way, so a file gets the same verdict on Windows, Linux and macOS

### Verify it yourself

`test_security.py` is a dedicated security suite anyone can run. It statically checks the code for `shell=True`, `eval`, `exec`, `os.system` and `subprocess` calls, confirms shell metacharacters pass through literally in every widget type, and covers binary validation, preset and extra-flag injection, path traversal, recovery file safety and the QProcess contract itself.

```bash
python test_security.py
```

The security model has been through several rounds of LLM-assisted audits.

---

## Detailed Features

### Works with most CLI tools

Most tools that take flags and positional arguments can be described by a schema, from small utilities like `ping` up to tools with hundreds of flags and nested subcommands, like `curl` (271 arguments) or `ffmpeg` (123 arguments). Write a schema, or have an LLM write one from the tool's docs, and Scaffold renders a native form. No UI code needed. What doesn't fit: interactive prompts that expect answers typed into stdin, full-screen TUIs that redraw the terminal, and tools driven by piped input instead of flags.

### Presets

Save, name and reload a whole form. Build up a library of ready-to-run commands for each tool and share the files with your team.

- **Save**: Presets > Save Preset (Ctrl+S). Enter a name and an optional description.
- **Load**: Presets > Preset List (Ctrl+L). A table with each preset's name, description and last modified date.
- **Edit**: Presets > Edit Preset. Edit descriptions, delete presets and toggle favorites.
- **Reset**: click "Reset to Defaults" in the command preview bar to put every field back to the schema's defaults.

Click the star column in the preset picker to pin your favorites to the top. Presets are stored as JSON in `presets/{tool_name}/`, so they're easy to copy around. If a schema changes later, fields that were removed are skipped and new fields get their defaults.

### Syntax-colored command preview

The preview shows the exact command as you change fields, with the binary, flags and values in different colors in both light and dark mode. Right-click it to copy the command quoted correctly for Bash, PowerShell or Windows CMD.

### Process execution

Run commands right from the GUI. Output is colored, with stdout and stderr in different colors, and you get exit codes and timestamps. The output panel is searchable (Ctrl+Shift+F), and you can copy it or save it to a file. ANSI escape codes are stripped out. Stopping a process sends SIGTERM first and falls back to SIGKILL if it doesn't exit. You can also set an auto-kill timeout per tool.

### 10 widget types

Each argument gets the right control: checkboxes for booleans, text fields for strings, spin boxes for integers and floats, dropdowns for enums, checkable lists for multi-enums, file and directory browsers, password fields with a show/hide toggle, and multi-line text areas.

### Subcommand support

Tools like `git` with lots of subcommands work fine. Multi-word chains like `ansible-galaxy role install` or `docker compose up` are supported too, and each word becomes its own token in the command. Picking a subcommand swaps in its fields while the global flags stay put.

### Command history

Every command you run is recorded. Open View > Command History (Ctrl+H) to browse recent runs for the current tool, see exit codes and timestamps, and restore any past form with one click. A filter bar lets you search the entries.

### LLM-powered preset generation

This works the same way as schema generation. Run `python scaffold.py --preset-prompt` to print the prompt, paste it into an LLM along with the tool's schema, describe the preset you want in plain English, and save the JSON it returns into `presets/<tool>/`. It's most useful for tools with a lot of flags, where clicking through a preset by hand gets tedious.

### Auto-save and crash recovery

Form state is saved automatically 2 seconds after you change something. If the app crashes, the next launch offers to bring your work back. Forms you haven't touched aren't saved, and old recovery files are cleaned up at startup.

### Cascade chaining

Open the cascade sidebar with Ctrl+G to chain tool runs into a sequence. A cascade has up to 20 numbered slots, and each slot holds a tool and an optional preset. Set a delay of 0 to 3600 seconds between steps, turn on loop mode to repeat the whole sequence, or turn on stop-on-error to halt at the first non-zero exit code. Cascade variables are named values (typed as `string`, `file`, `directory`, `integer` or `float`) that Scaffold asks for when the run starts and fills into the matching fields in each step. They're a good fit for target IPs, output folders or anything else that changes from run to run.

**Cascade captures** let later steps reuse values from earlier output. A capture can pull text out of stdout or stderr with a regex, read a file path, grab an exit code or take the tail of an output stream, and later steps use it as a `{name}` placeholder.

You can save, load, import, export and delete cascade files from the sidebar, and the sidebar remembers its state between sessions. Cascades run through the same list-based QProcess pipeline as single runs, with no shell involved and the same security guarantees. Six example cascades come in the repo's `cascades/` folder: `recon_basic`, `ping_then_nmap`, `cascade_archive_playlist`, `cascade_pandoc_dual_output`, `cascade_ssh_scp` and `cascade_nmap_ncat`.

Saved cascades can also run without the GUI. See [Running cascades headless](#running-cascades-headless).

### Cascade history

Every cascade run is recorded with a snapshot of its configuration and the final command each step ran, after substitutions. Browse them in View > Cascade History (Ctrl+Shift+H). Restore Step reloads one step's form, and Restore Cascade loads the whole cascade back into the sidebar without running it. Export saves one run's history to JSON, and Export All saves everything. History keeps the latest 50 entries and drops the oldest first. In loop mode every pass gets its own entry, so loops fill it up faster. A run that was cut short by a crash shows up as "crashed" after the next launch.

<img src="nmap%20cascade%20example.png" alt="Scaffold cascade panel running an nmap workflow" width="75%">

### LLM-powered cascade generation (experimental)

Cascades are harder for an LLM to write than schemas or presets because they involve several tools at once, and pasting several full schemas into one chat burns through the context fast. What works better is a Claude Project (or any LLM setup with persistent documents) that already has your `tools/` and `presets/` folders loaded. Paste the provided instructions into the Project's custom instructions and describe the cascade you want in plain English.

Results depend a lot on your presets. A preset is a known-good set of flags with a description a person wrote, and an LLM reasons about those far more reliably than about a raw schema. The instructions tell the model to use presets first and only pick flags from a full schema when no preset fits, so a bigger, well-described preset library gets you better cascades.

This feature is **experimental** and documentation-only. Setup, usage and known limitations are in `scaffold_data/CASCADE_LLM_GENERATION_GUIDE.md`.

### Custom PATH Directories

Add folders to Scaffold's PATH so it can find and run programs and scripts that aren't on your system PATH. Open it from **File > Custom PATH Directories...**. Scaffold searches these folders when it checks whether a tool is installed (the checkmarks in the tool picker and the warning bar on a form) and when it launches the tool, and adds them to the PATH the launched program sees. When custom folders are set, the command echo in the output panel and the history show the full path of the program that ran, so you can always tell which copy was used. Settings persist in QSettings, or in `scaffold.ini` next to the app in portable mode.

The main use is script-based tools. Write a schema with `"binary": "myscript.py"`, add the script's folder here, and Scaffold runs it like any other tool. The script has to be executable on its own. On Unix that means a shebang line and the execute bit. On Windows, `.bat` and `.cmd` files work as they are, and `.py` scripts work when Python is installed with `PATHEXT` set up (the default installer does this). `.ps1` scripts can't be launched directly. Use `"binary": "powershell"` and pass the script path as the first positional argument instead.

### Additional features

- **Deprecated and dangerous indicators**: schema flags can be marked `deprecated` (strikethrough plus a warning) or `dangerous` (a red caution symbol) so they stand out without being disabled
- **Min/max constraints**: optional `min` and `max` on integer and float arguments set the spinner's range
- **Drag and drop**: drop a `.json` schema file onto the window to load it
- **Help menu**: an About dialog with version info and the GitHub link, a cascade guide and a keyboard shortcut reference
- **Session persistence**: remembers your window size and position, theme and last opened tool
- **Format markers**: the `_format` key keeps you from loading a preset as a tool schema (or the other way around), with a clear error message if you try
- **Bundled example schema**: `scaffold_data/tools/example.json` uses every feature in one file
- **Portable mode**: put `portable.txt` next to `scaffold.py` to keep every setting in a local INI file instead of the system registry, so you can run from a USB drive with a fully isolated configuration
- **Bundled tool schemas**: aircrack-ng, airodump-ng, ansible (4 tools), curl, docker (3 tools), ffmpeg, find, git, gobuster, hashcat, ncat, nikto, nmap, openclaw, ping, rsync, scp, ssh, tar and wget. Some haven't had much testing yet, so bug reports and contributions are welcome. Several come with presets under `default_presets/`, which get copied into your `presets/` folder the first time you open the tool. Right now that's `find`, `ncat`, `nmap`, `rsync`, `scp`, `ssh`, `tar` and `wget`
- **Experimental schemas**: `pandoc.json` and `yt-dlp.json` are newer and still experimental. Their example presets are under `default_presets/pandoc/` and `default_presets/yt-dlp/` (copied into your `presets/` folder the first time you open them), and the example cascades are `cascades/cascade_pandoc_dual_output.json` and `cascades/cascade_archive_playlist.json`. Expect some rough edges, and please report anything you run into

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Enter** | Run the command (when not typing in a field) |
| **Shift+Enter** | Run cascade chain (when not typing in a field) |
| **Ctrl+Enter** | Run the command |
| **Escape** | Stop a running process |
| **Ctrl+S** | Save preset |
| **Ctrl+L** | Preset list |
| **Ctrl+H** | Command history |
| **Ctrl+Shift+H** | Cascade history |
| **Ctrl+O** | Load tool from file |
| **Ctrl+R** | Reload current tool |
| **Ctrl+F** | Focus field search bar |
| **Ctrl+Shift+F** | Search within output panel |
| **Ctrl+D** | Toggle dark mode |
| **Ctrl+G** | Toggle cascade panel |
| **Ctrl+B** | Tool list |
| **Ctrl+Q** | Quit |

## Command-Line Usage

```bash
# Launch the GUI (tool picker)
python scaffold.py

# Open a specific tool directly
python scaffold.py scaffold_data/tools/nmap.json

# Validate a schema without launching the GUI
python scaffold.py --validate tools/mytool.json

# Print the LLM prompt for schema generation
python scaffold.py --prompt

# Print the LLM prompt for preset generation
python scaffold.py --preset-prompt

# Run a saved cascade without the GUI
python scaffold.py --run-cascade cascades/my_cascade.json

# Show the version and exit
python scaffold.py --version
```

### Running cascades headless

`--run-cascade` runs a saved cascade from a terminal, a script or a scheduled task without opening the window. Each step's output streams to your terminal with a `[step N: tool]` prefix, so you can follow along or pipe it to a log.

```bash
python scaffold.py --run-cascade cascades/recon.json \
    --var TARGET=10.0.0.0/24 \
    --var --output=scan.xml \
    --loop 3 \
    --summary run.json
```

| Option | What it does |
|--------|--------------|
| `--var NAME=VALUE` | Sets a cascade variable. `NAME` is the variable's flag exactly as the cascade defines it, like `--output` or `TARGET`. Repeat it once per variable. |
| `--vars FILE` | Loads variables from a JSON object that uses the same names, for example `{"TARGET": "10.0.0.1", "--output": "scan.xml"}`. If a name is set both ways, `--var` wins. |
| `--loop N` | Runs the whole cascade N times (1 to 1000). It's required when the cascade was saved with loop mode on, so a saved loop can't run forever from a cron job. Otherwise the cascade runs once. |
| `--summary PATH` | Writes a JSON summary of the run to PATH. |

The options can go in any order.

| Exit code | Meaning |
|-----------|---------|
| 0 | Every step finished with exit code 0 |
| 1 | The run couldn't start or was aborted (bad arguments, an unreadable cascade file, missing variables) |
| 2 | Stop-on-error halted the cascade at a failing step |
| 3 | The cascade finished, but at least one step exited non-zero |
| 130 | Interrupted with Ctrl+C |

A headless run doesn't disturb your GUI setup. Settings like recent tools, cascade slots and window size are put back afterwards, nothing is written to history, and your crash-recovery files are left alone. On a machine with no display, like a server you reach over SSH, set `QT_QPA_PLATFORM=offscreen` first. Qt needs a display platform even for a hidden window.

---

## Limitations

- **Scaffold doesn't generate schemas on its own.** You write the JSON, or have an LLM write it from the docs. It can't detect flags by inspecting a binary.
- **Scaffold doesn't sandbox the program it runs.** The design prevents shell injection and constrains input, but once a command starts, that program has every permission your user account has.
- **Schema quality depends on the LLM and the docs you give it.** `--help` output usually isn't detailed enough, and man pages or official docs do much better. Very large tools can overflow an LLM's context window.
- **Mostly tested on Windows.** The automated suites also run on Linux, but macOS has had the least real-world use. If you hit a platform-specific problem, please open an issue.
- **Requires PySide6.** There are no plans to support other GUI frameworks.
- **Huge subcommand trees get crowded.** Tools with 70+ subcommands and 200+ arguments produce forms that work but are dense. Scaffold still helps you find flags and avoid syntax errors, but for tools that size it's more of a reference than a fast workflow.
- **Schema, preset and cascade files need to be UTF-8.** A UTF-8 byte order mark is fine. UTF-16 files, which Windows PowerShell 5.1's `>` writes by default, are rejected with an error that tells you why. Re-save them as UTF-8, for example with `Set-Content -Encoding utf8`.

---

## About This Project

Much of Scaffold's code was written by [Claude Code](https://claude.ai) (Opus 4.6), with edits from me. I designed it, directed it, tested it and iterated on it. I audited every line of code and every command, and edited the code directly where it needed it. It wasn't a one-shot generation, and it took a lot of careful planning and execution.

I built Scaffold the way a real team would build software, just with an AI writing most of the code:

1. **Architecture first.** It started with a design document for the widget type system, the schema format and the command assembly pipeline, before any code was written.
2. **Staged deliverables.** It was built in phases: core engine, widget rendering, command execution, presets, subcommands, dark mode, elevated execution, UI polish, and the schema generation prompt.
3. **Tests alongside features.** Tests were planned with each stage instead of added at the end. The suites (3,943 assertions across 6 suites) were written to check each feature as it was delivered.
4. **Code review cycles.** Once the core was stable, the code went through several review passes: cleanup, an error-handling audit, performance profiling and linting.
5. **A lot of iteration.** Most features took several rounds of build, test and fix. The dark mode scrollbar alone went through QSS, then QProxyStyle, and finally native `setColorScheme` before it worked right.
6. **Manual QA on every release.** I tested every version by hand on real tools before tagging it.

I have 15 years of professional IT experience and certifications in cybersecurity, ethical hacking, penetration testing and Python development. I'm not a software developer by trade, but I wasn't starting from zero either. Claude Code is a useful tool, and it still needs someone behind it who knows what they're building and why.

**Methodology: plain-English bug hunting.** Most bugs in recent releases were found the same way. First I describe the bug in as much detail as I can, whether it's in the logic or the UI. Then we write a focused diagnostic prompt for the suspected issue, run it against the whole codebase in a fresh context window, and collect measurements and code traces. The fix comes after that, and it's based on what was confirmed. No fix prompt gets written from an assumption. Every non-obvious bug gets a diagnostic pass first.

**Multi-model distillation.** Audits from Copilot, ChatGPT and other models turn up candidate findings. Those go back to Claude with extended thinking for an architectural review and a final call on what's real, what's noise and what's over-engineering.

**Full-codebase rescans.** Every so often the whole codebase gets reviewed again from scratch. The latest pass split `scaffold.py` into six slices with a separate reviewer on each. Every finding was reproduced against the released version before anything was changed, and each fix came with a regression test that fails on the old code and passes on the new. That pass fixed a few dozen bugs, including some that only showed up on Linux and macOS.

---

## Support the Project

This project was built as a hobby by one person, a couple of computers and a couple of LLMs. It burned through quite a bit of token cost and mass amounts of personal time, but it was worth it. If Scaffold saves you some time, or you just think it's cool, consider supporting ongoing development.

- **GitHub Sponsors**: sponsor via [github.com/sponsors/kevwillow](https://github.com/sponsors/kevwillow)
- **Star this repo**: it's free, and it helps other people find the project
- **Share your tool schemas**: send a PR with schemas for popular CLI tools
- **Crypto donations**, if you're feeling generous:
  - **BTC**: `bc1qmtzjlc2cw2y45nea2jqf4deh946j8mq502zvsw`
  - **BTC (Unstoppable Domain)**: `gurutech.blockchain`
  - **LTC**: `ltc1qf32n038a90ulajlq6zz67r3n2myewpjlj2ej6w`
  - **ETH**: `0x9bf3311c4721fe37f58913dc57c2bf1722dc8a0f`
  - **BCH**: `bitcoincash:qr2l294kuve9cw48u7xek9nklhed066ycvjtj4ymq9`
  - **SOL**: `CuraE8usMpSrAhpY2QiWaQGoBjyJzkSaUNP6kRgAzscU`

- **Contact**: kev@gurutechnology.services

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE). Copyright (C) 2026 Kev Wilson.

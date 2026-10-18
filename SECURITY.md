# Security Policy

## Supported versions

Security fixes go into the latest release. If you're on an older version, please upgrade before reporting, since the issue may already be fixed.

## Reporting a vulnerability

Please don't open a public issue for a security problem.

Report it privately instead, using either of these:

- **GitHub private vulnerability reporting**: go to the repo's **Security** tab and click **Report a vulnerability**
- **Email**: kev@gurutechnology.services

It helps a lot if you include the Scaffold version, your OS and Python version, the steps to reproduce it, and what an attacker could do with it. A minimal schema, preset or cascade file that triggers the problem is ideal.

Scaffold is maintained by one person as a hobby, so I can't promise a response time, but security reports get looked at before anything else. Once it's fixed, I'm happy to credit you in the changelog if you'd like.

## What counts as a security issue

Scaffold's job is to turn form fields into an argument list and hand it to `QProcess` without a shell. Things that break that promise are in scope, for example:

- getting shell syntax, an extra argument or a flag injected into the command through a field, a preset, a cascade variable, a cascade capture or the Additional Flags box
- a cascade or preset file that reads or writes outside the Scaffold folders
- "Copy as Bash / PowerShell / CMD" output that a shell would interpret differently from what the preview shows
- a password value showing up unmasked in the preview, output, history or clipboard
- crash-recovery or history files that leak data to other users on the same machine

Some things are out of scope because they're how Scaffold is designed to work:

- **The program you run.** Scaffold doesn't sandbox the tool it launches. Once a command starts, that program has your user account's permissions.
- **Schemas you choose to load.** A schema decides which binary runs. Only load schemas from people you trust, the same way you'd only run their scripts.
- **Elevated runs.** When you tick "Run elevated", the command runs with the privileges you approved.

## How the code is checked

Every pull request and push to `main` runs these checks, and the CI and CodeQL workflows also re-run them weekly:

- the six test suites, including the dedicated security suite (`test_security.py`), on Windows, macOS and Linux across every supported Python version, plus the oldest PySide6 version Scaffold supports
- CodeQL analysis of the Python code and of the workflow files themselves
- Bandit and Ruff static checks, and a repo check that `shell=True`, `eval`, `exec` and `os.system` never appear in the app
- `pip-audit` on every pinned dependency, and GitHub's dependency review on any PR that changes dependencies
- actionlint and zizmor on the workflows; every action is pinned to a full commit SHA and every Python dependency is pinned with hashes
- an OpenSSF Scorecard run on `main`

# Security

## Reporting a vulnerability

Open a [private security advisory](https://github.com/tdries/td-claude-plugin-popr/security/advisories/new).
Please do not open a public issue for anything exploitable. Expect a first
response within a week.

## What POPR does on your machine

Worth knowing before you install anything that hooks into your editor:

- **Runs on every turn.** Four Claude Code hooks invoke `bin/popr`. It reads the hook payload on stdin, and may read the tail of the session transcript to build the notification preview.
- **Edits `~/.claude/settings.json`.** `popr install` adds four hook entries, having copied the file to `settings.json.popr-backup` first. `popr uninstall` removes them.
- **Builds and ad-hoc signs an app bundle.** `popr install` copies terminal-notifier's `.app` to `~/Applications/POPR.app`, restamps its identity and icon, signs it with `codesign --sign -` and registers it with LaunchServices. No certificate and no network access is involved; everything is local.
- **Sends nothing anywhere.** No network calls, no telemetry, no analytics. Your project names, branch names and Claude's replies stay on the machine. The only thing written outside `~/.claude`, `~/.config/popr` and `~/Applications/POPR.app` is the log at `~/Library/Logs/popr.log`.

## The one injection surface, and how it is handled

`terminal-notifier` takes its text as command line arguments. Text that POPR
passes through comes from Claude's output and from hook payloads, which is to say
it is not trusted. A message beginning with `-` would be parsed as a flag rather
than as text.

`clean()` in `bin/popr` strips leading whitespace, quotes, brackets and dashes
from every string before it reaches the notifier, and `tests/test.sh` asserts it,
including the case of a message that tries to smuggle in `-execute`.

The click action is built by POPR from the detected app and the project
directory, both quoted with `printf %q`, and never from notification text.

## Scope

POPR is macOS only and runs entirely as your user. It requests no entitlements
and no elevated privileges, and the installer never uses `sudo`.

# Contributing to POPR

POPR is one bash script, a logo generator and some packaging. That is deliberate.
The bar for adding anything is: **would a user notice it was missing?**

## Setup

```bash
git clone https://github.com/tdries/td-claude-plugin-popr.git
cd td-claude-plugin-popr
brew install jq terminal-notifier shellcheck
./install.sh                     # installs from your clone
```

`./install.sh` points `~/.local/bin/popr` at a copy in `~/.local/share/popr`, so
rerun it after editing `bin/popr`.

## Before you open a PR

```bash
tests/test.sh                                                  # must be all green
shellcheck bin/popr install.sh tests/test.sh "packaging/Install POPR.command"
python3 assets/make_logo.py --demo                             # only if you touched the logo
```

CI runs exactly these on a macOS runner.

## Testing without spamming yourself

Everything in `tests/test.sh` runs under `POPR_DRY_RUN=1`, which prints what
would be posted instead of posting it, mutes sounds, and never touches
`~/.claude/settings.json`. Use it:

```bash
POPR_DRY_RUN=1 POPR_APP=Cursor bin/popr stop <<'JSON'
{"session_id":"x","last_assistant_message":"hello"}
JSON
```

Add an assertion for any behaviour you change. Tests that need a fixed
environment should set `POPR_APP`, `POPR_CONFIG` and `POPR_BUNDLE` so results do
not depend on the developer's own machine.

## House rules

- **A hook must never break a turn.** Every path in `bin/popr` exits 0, and all slow work runs in a detached subshell. A change that can make Claude wait or fail is not acceptable, however useful it is.
- **Four spaces** in bash and Python, two in JSON and YAML.
- **No new runtime dependencies.** `jq` and `terminal-notifier` are the entire list and it should stay that way. The logo generator is standard library only, on purpose.
- **Commit messages**: imperative subject under ~50 chars, and a body explaining *why* rather than what. The diff already says what.
- Branches: `feature/<thing>`, `fix/<thing>`.

## Where things live

| Path | |
|---|---|
| `bin/popr` | the whole engine |
| `assets/make_logo.py` | the logo, as a pixel grid; everything else in `assets/` is generated |
| `.claude-plugin/` | plugin manifest and marketplace entry |
| `packaging/` | Homebrew formula, npm shim, double click installer |
| `docs/DESIGN.md` | why it is built this way, including what macOS refuses to allow |

Read `docs/DESIGN.md` before proposing anything structural. Several obvious ideas
(animated banner icon, custom banner layout, a `.pkg`) are already recorded there
as impossible or deliberately rejected, with the reasoning.

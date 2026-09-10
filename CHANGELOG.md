# Changelog

All notable changes to POPR. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/).

## [1.0.0] - 2026-09-10

First public release. POPR is a rename and repackage of Butlr v2.1.0, which was
never distributed outside its author's laptop.

### Added
- `popr install` / `popr uninstall`, registering the four hooks in `~/.claude/settings.json` in pure bash. Butlr needed Python for this.
- `popr config`, interactive settings written to `~/.config/popr/config.json`, plus that file as a resolution layer between plugin options and the defaults.
- Double registration guard: installing over an existing plugin install is refused, because it would fire every notification twice. `popr doctor` reports the condition.
- Butlr migration: `popr install` strips leftover butlr hooks and removes `~/.claude/skills/butlr`.
- `POPR_DRY_RUN=1`, which prints what would be posted instead of posting it. The test suite is built on it.
- `tests/test.sh`, 21 assertions covering the three notification payloads, truncation, settings precedence, worktree resolution, argument injection, and the never-break-a-turn contract.
- Four install channels: Claude Code plugin, Homebrew, curl, npm.
- Pixel confetti logo in the Anthropic palette, generated from a single grid by `assets/make_logo.py` using only the Python standard library.

### Fixed
- Symlink safe root resolution. Butlr derived its package root from `dirname $0/..`, which under Homebrew or any symlinked install resolved to the wrong directory and lost the bundled banner icon.
- Config file values are read with `has($k)` rather than jq's `//` operator, which would have silently swallowed a stored `false`.

### Changed
- `BUTLR_*` environment variables are now `POPR_*`. There is no compatibility alias.
- Log moved from `~/Library/Logs/butlr.log` to `~/Library/Logs/popr.log`.

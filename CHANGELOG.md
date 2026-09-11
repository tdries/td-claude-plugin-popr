# Changelog

All notable changes to POPR. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/).

## [1.6.1] - 2026-09-11

### Fixed
- **Clicking a banner did nothing.** Click to return to the window is the reason POPR exists, and it had been broken since 1.3.0 replaced macOS notifications with our own windows. Three separate faults, each hiding the next:

  1. `NSView` refuses "first mouse" clicks by default. macOS treats a click into a non-key window as a request to activate it, and POPR's panel is deliberately non-activating so it never steals focus — so every click it ever received was a first-mouse click, and every one was discarded.
  2. Even with that fixed, `mouseDown:` still never fired. Mouse events reach a window through NSApplication's event queue, and `NSRunLoop.runUntilDate` does not drain it; it only services run-loop sources. The banner drew perfectly and was never sent a single event.
  3. Draining the queue by hand and calling `sendEvent` killed the process outright, so the banner stopped appearing at all.

  The wait is now `[NSApp run]`, which dispatches events properly, ended by the click handler or a timed stop. Still fully event driven, so an idle banner costs no measurable CPU.

  Only the third fault announced itself. The first two were completely silent, which is the failure mode this codebase keeps producing — and why the awkward-input test asserts the banner returns `clicked` or `timeout` rather than merely not crashing: that assertion catches exactly the third fault.

## [1.6.0] - 2026-09-10

### Fixed
- **A long project name pushed the status off the banner.** On one fixed line, a name like `a-really-long-monorepo-package-name · feature/some-branch` ran to 104 characters and clipped the seven word status entirely — the one thing that must always be readable. Title and status are now budgeted separately: the status keeps the width it needs and the name gives way.
- **A banner that failed to draw took the notification with it.** It was launched detached with its output discarded, so a failure was silent and you simply got nothing. POPR now reads the outcome and falls back to a macOS notification when the banner errors *or* dies without printing anything at all, which is how both of this project's worst bugs presented. Both shapes have tests, using a deliberately broken banner.

### Added
- **VoiceOver.** A borderless non-activating panel is invisible to screen readers, which made POPR strictly worse than the notification it replaced for anyone using one. Banners are now announced.
- Hostile input tests: a project directory containing spaces, semicolons, quotes and `$(...)` cannot execute anything through the click command, and banner text is never evaluated as shell. Plus 300 character names, empty status and unicode.
- `POPR_LOG`, so the log can be redirected — which is what makes the fallback testable.

## [1.5.0] - 2026-09-10

Acting on an honest reading of what was weakest.

### Fixed
- **An open banner cost about 2% of a core doing nothing.** It woke twenty times a second to ask whether it had been clicked yet. The click handler now stops the run loop itself, so the banner idles in five second blocks and the wake is only a backstop for the deadline. Three open banners went from 6.4% CPU to 0.0%, and dismissal is still immediate.

### Added
- **Tests for the hook wiring**, which rewrites `~/.claude/settings.json` and was the riskiest thing POPR does with no coverage at all — every other test runs under `POPR_DRY_RUN`, which skips exactly that path. Fourteen assertions against a throwaway Claude directory: registers exactly four hooks, is idempotent, keeps unrelated settings and other people's hooks, strips leftover butlr ones, backs the file up first, works from no file at all, refuses to wreck an unparseable one, and refuses to stack on a plugin install. Plus concurrent slot claiming.
- `POPR_CLAUDE_DIR` so that path can be tested against a copy, and `popr install --quiet` for scripted installs, which is also what lets those tests run without throwing windows on screen.

### Changed
- **The branded app bundle is built only when `native` is turned on.** It exists solely to give macOS notifications POPR's name and icon, and those are off by default, so every install was doing work nobody had asked for.

## [1.4.0] - 2026-09-10

Hardening pass.

### Fixed
- **POPR could hold up the hook that called it.** The banner was launched in a background subshell that still held the parent's stdout, so the calling shell waited for it — and a banner that waits for a click waits a long time. `popr install` hung outright, and in a `Stop` hook it would have stalled Claude for up to fifteen minutes per turn. The subshell now gives up its inherited stdio, and a test times the real path end to end rather than asserting about the source.
- `banner_style: minimal` was documented in the plugin settings, the README and `popr help`, but nothing branched on it any more after the one-line rewrite. Removed rather than left as a setting that quietly does nothing. `pill` and `glass` are both real.

### Changed
- **`terminal-notifier` is no longer required.** POPR draws its own banners, so it is only needed for the optional native path. Installing no longer fails without it, and `popr doctor` lists it as optional. `jq` remains the one hard dependency.
- The banner appears on the screen the **pointer** is on. On a two screen desk, "main" is wherever the menu bar lives, which is regularly not the one you are looking at.
- `popr uninstall` closes any open banners and clears its state directory instead of leaving processes running.
- `popr config` covers confetti, status length, banner style and font; passing an empty sound now means "POPR's own" rather than pinning a macOS one.

### Added
- `tests/banner-rules.js`: the mark and burst rules checked against eight project names including unicode and single characters — six chips, all six colours exactly once, nothing outside the icon, mass within a pixel of centre, deterministic per name, and different between names.

## [1.3.1] - 2026-09-10

### Fixed
- `popr doctor` reported "confetti on, but assets are missing" on a perfectly working install. It was still checking for `burst.gif` and `overlay.js`, which the procedural rewrite deleted. A health check that cries wolf is worse than no health check, so it now checks what the confetti actually needs and names the project the burst is seeded from.

## [1.3.0] - 2026-09-10

POPR stops using macOS notifications and draws its own banners.

### Added
- **Its own banners.** A non-activating panel, 470x30, ivory pill, one line, staying until clicked. macOS notifications are no longer posted at all by default. The reason is §4.5 of the design: the layout is fixed, the app-bundle icon cannot be removed (a fully transparent `.icns` renders a white square, verified on a bundle id macOS had never seen), and nothing inside a notification will animate. No alternative notifier avoids any of it, because they all post through `UNUserNotificationCenter`.
- **Confetti DNA.** Every project gets its own mark and its own burst, seeded from the project name with FNV-1a and drawn procedurally. Every mark carries all six brand colours exactly once, every burst all four explosion colours twice, so arrangements differ but weight never does.
- **The burst comes out of the mark**, which only became possible once we drew the banner ourselves and therefore knew where it was.
- **Three synthesized sounds** sharing one timbre: settled on finish, rising and unresolved when Claude needs you, minor and falling on error.
- Settings: `banner`, `banner_style`, `banner_icon`, `banner_seconds`, `native`, `font`, `summary_words`.

### Changed
- The banner shows a **status, not an excerpt**: the first sentence of Claude's reply, at most seven words, never an ellipsis.
- Typographic marks `✓ ⋯ ✕` replace emoji.
- The logo is down to eight pieces, none smaller than three cells.
- Confetti reach halved to 90px.

### Removed
- `burst.gif`, `overlay.js`, the GIF generator and the Pillow development dependency. The burst is procedural now, so there is no animation asset to keep in sync with the mark.

## [1.1.1] - 2026-09-10

### Changed
- The explosion has its own palette, separate from the logo's: `#C15F3C`, `#FFFFFF`, `#F4F3EE`, `#B1ADA1`. The logo is a mark that has to hold up on ivory and in a settings list; the burst is thrown over whatever happens to be on the desktop, and wants more contrast and fewer mid-tones.

## [1.1.0] - 2026-09-10

### Added
- A confetti burst when a turn finishes: an animated pixel burst in the corner of the screen, from the same grid as the logo.

  macOS will not animate anything inside a notification. The banner icon comes from the app bundle as a static `.icns`, and an animated GIF handed over as the content image renders as its first frame and stops, which we tested rather than assumed. Every macOS notifier posts through the same `UNUserNotificationCenter`, so no alternative tool avoids it; the banner is drawn by the OS.

  So POPR stops asking the notification system for motion and draws its own window instead: borderless, transparent, click through, above everything, gone in about a second. A JXA script run by `osascript`, which ships with macOS, so it adds no dependency and needs no Xcode. Only on a finished turn; a permission prompt or an error gets none. `POPR_CONFETTI=false` disables it, `POPR_CONFETTI_SIZE` resizes it.

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
- Pixel confetti logo in the Anthropic palette, generated from a single grid by `assets/make_logo.py` using only the Python standard library: static SVG, animated SVG, seven PNG sizes and the macOS `.icns`.
- POPR posts through its own app bundle, so banners carry POPR's name and confetti icon and macOS gives POPR its own row in System Settings. `popr install` builds it from terminal-notifier's bundle and ad-hoc signs it locally, which is why it needs no Apple Developer ID. `popr doctor` flags a bundle left stale by a terminal-notifier upgrade, and POPR falls back to plain terminal-notifier if it cannot build one.
- The bundle declares the persistent Alerts style, so a notification waits for your click rather than vanishing. Verified on macOS 26.5.
- The app icon is drawn on an ivory rounded body. Bare confetti on transparent has no mass and dissolves into a grey smudge at the 16 and 32 px sizes where an app icon actually lives. The banner image stays transparent, since it sits on the banner's own dark background.

### Fixed
- Symlink safe root resolution. Butlr derived its package root from `dirname $0/..`, which under Homebrew or any symlinked install resolved to the wrong directory and lost the bundled banner icon.
- Config file values are read with `has($k)` rather than jq's `//` operator, which would have silently swallowed a stored `false`.

### Changed
- `BUTLR_*` environment variables are now `POPR_*`. There is no compatibility alias.
- Log moved from `~/Library/Logs/butlr.log` to `~/Library/Logs/popr.log`.

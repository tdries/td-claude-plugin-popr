# POPR · design

Status: approved 2026-09-10. Supersedes Butlr v2.1.0.

POPR gives you a clickable macOS notification when a Claude Code session finishes,
needs a permission, or hits an error. Click the banner and the window that session
lives in comes to the front.

It is a port of Butlr, renamed, repackaged, and distributed through every channel
that installs cleanly without an Apple Developer ID.

---

## 1 · Constraints that shaped this

| Constraint | Consequence |
|---|---|
| No Apple Developer Program membership | No `.app`, no `.pkg`, no `.dmg`, no `--cask`. Anything signed is out. An unsigned bundle on macOS 15+ throws a Gatekeeper wall that is a worse first run than a `brew` command. |
| macOS takes a notification's icon and name from the posting bundle, with no API to override either | POPR posts through its **own** restamped copy of terminal-notifier's bundle, built locally at install time. See §4.4. |
| A hook must never break a turn | Every path in `bin/popr` exits 0. All slow work runs in a detached subshell. |
| macOS only | `uname` guard in the installer and the formula. |
| A hook must return at once | The banner outlives the process that launched it, so it is fully detached, stdio included. Redirecting the command inside the subshell is not enough: the subshell still holds the parent's stdout and the caller waits on it. Timed by a test. |

## 2 · What ships

| Artifact | User command | Notes |
|---|---|---|
| Claude Code plugin | `/plugin marketplace add tdries/td-claude-plugin-popr`<br>`/plugin install popr@popr` | Primary channel. Repo root is the plugin. |
| Homebrew formula | `brew install tdries/tap/popr` | Needs a second repo, `tdries/homebrew-tap`. |
| curl installer | `curl -fsSL https://raw.githubusercontent.com/tdries/td-claude-plugin-popr/main/install.sh \| sh` | For machines without Homebrew. |
| npm package | `npx popr-cli install` | Unscoped name `popr-cli`, already free. Binary on PATH is `popr`. |
| GitHub Release tarball | manual download | Cut by CI on tag. |
| `Install POPR.command` | double click | Bundled in the release zip. Shows one Gatekeeper warning; README documents right click → Open. |

## 3 · Repo layout

Repo root is simultaneously the marketplace and the plugin, which is a supported
and field proven shape (`"source": "./"`).

```
.
├── README.md                     marketing surface: hero, four install paths, settings, troubleshooting
├── LICENSE                       MIT
├── CHANGELOG.md                  keep a changelog format
├── install.sh                    curl | sh entrypoint, also what the .command execs
├── bin/popr                      the engine, bash
├── hooks/hooks.json              plugin hook wiring, uses ${CLAUDE_PLUGIN_ROOT}
├── skills/test/SKILL.md          /popr:test
├── assets/
│   ├── make_logo.py              pixel grid -> svg + animated svg + png + icns
│   ├── logo.svg                  generated
│   ├── logo-animated.svg         generated, SMIL burst, README hero
│   ├── icon-512.png              generated, the app icon on its ivory body
│   ├── banners.svg               hand authored, README illustration
│   ├── social.svg                hand authored, GitHub social preview
│   ├── POPR.icns                 generated, the bundle's icon
│   └── popr-{16,32,64,128,256,512}.png   generated, 256 is the banner icon
├── docs/
│   └── DESIGN.md                 this file
├── packaging/
│   ├── popr.rb                   brew formula, copied into the tap by CI
│   ├── npm/package.json          name popr-cli, bin popr
│   ├── npm/bin/popr.js           two line shim execing ../../bin/popr
│   └── Install POPR.command      double click wrapper, execs install.sh
├── tests/test.sh                 dry run assertions, no real notifications
├── .claude-plugin/
│   ├── plugin.json               name popr, version, userConfig block
│   └── marketplace.json          name popr, plugins[0].source "./"
└── .github/workflows/
    ├── ci.yml                    shellcheck + tests on macos-latest, on push and PR
    └── release.yml               on tag v*: release, tap bump, npm publish
```

## 4 · The engine, `bin/popr`

Base is the installed Butlr v2.1.0 script (248 lines), not the v2.0.0 zip. It is
ahead: git worktree resolution, Claude Desktop detection through the transcript
`entrypoint`, tighter option resolution.

### 4.1 Ported unchanged

- Modes `stop`, `attention`, `error`, `clear` driven by four hooks.
- Process tree walk (max 30 hops) to find the `.app` bundle that launched Claude,
  so the click refocuses the right editor window via `open -a <app> <project dir>`.
- Editor allowlist: VS Code, Cursor, Windsurf, VSCodium, Kiro, Trae. Everything
  else gets a plain app activation.
- Per session banner group `popr-<session_id>`, so N sessions means at most N
  banners, and `clear` removes that session's banner on your next prompt.
- Summary extraction: `.last_assistant_message`, falling back to the last text
  block in the transcript tail, stripped of markdown, truncated to 140 chars.
- Git branch from `.git/HEAD`, including the `gitdir:` indirection for worktrees.
- Log at `~/Library/Logs/popr.log`, rotated at 256 KB.
- `clean()` strips leading whitespace, quotes, brackets and `-` from any string
  before it reaches `terminal-notifier`. This is not cosmetic: a message starting
  with `-` would otherwise be parsed as a CLI flag. It gets a test.

### 4.2 Changed

- `BUTLR_*` → `POPR_*`. No backwards compatible alias; POPR is a new name.
- Log path `butlr.log` → `popr.log`.
- Default banner icon `assets/mascot.png` → `assets/popr-256.png`.

### 4.3 Added

**New subcommands**

| Command | Does |
|---|---|
| `popr install` | Ensures deps, registers the four hooks in `~/.claude/settings.json`, fires a test notification. |
| `popr uninstall` | Removes POPR hooks from `~/.claude/settings.json`. Leaves the binary to the package manager. |
| `popr config` | Interactive prompts, writes `~/.config/popr/config.json`. |
| `popr version` | Prints `VERSION`, a literal at the top of the script. CI asserts it matches `.claude-plugin/plugin.json` and `packaging/npm/package.json`, so there is no runtime `jq` dependency just to print a number. |
| `popr help` | Usage. |

`install` and `uninstall` port the logic of Butlr's `setup_hooks.py` into bash,
so the tool has no Python dependency. They back `~/.claude/settings.json` up to
`.popr-backup` before writing, and they strip any existing hook whose command
contains `/popr/bin/popr` before adding, making them idempotent.

**Double registration guard.** Installing through both the marketplace and
Homebrew would fire every hook twice. `popr install` scans for an existing plugin
install (`~/.claude/plugins/**/popr`, `~/.claude/skills/popr`) and refuses with a
clear message unless given `--force`. `popr doctor` reports the same condition.

**Butlr migration.** `popr install` removes any hook whose command contains
`/butlr/bin/butlr`, and offers to delete `~/.claude/skills/butlr`. Without this
the one existing Butlr user gets two banners per turn.

**`POPR_DRY_RUN=1`.** Makes `notify()` print one parseable line to stdout instead
of calling `terminal-notifier`, and turns `play_sound` and `speak` into no ops.
This is the only reason the notification logic is testable at all, so it is part
of the design rather than a test helper.

**Symlink safe root resolution.** Butlr computed its own root as
`dirname $0/..`. Under Homebrew, `bin/popr` is a symlink from
`/opt/homebrew/bin/popr` into `libexec`, so that expression resolves to
`/opt/homebrew` and the bundled icon is never found. POPR walks `$0` through
symlinks before computing the root. Same bug would hit the curl install, which
also symlinks.

**Curl install layout.** `install.sh` places the payload in
`~/.local/share/popr/` and symlinks `~/.local/bin/popr` to
`~/.local/share/popr/bin/popr`. It warns if `~/.local/bin` is not on `PATH` and
prints the line to add. It refuses to run on anything but Darwin, and installs
`jq` and `terminal-notifier` through Homebrew when they are missing, or names
the missing dependency and exits if Homebrew is absent.

### 4.4 The branded bundle

Butlr shelled out to `terminal-notifier`, so every banner wore terminal-notifier's
icon and name, and each user had to grant notification permission to a tool that
was not the one they installed. This is not a cosmetic problem and it cannot be
argued away: terminal-notifier **removed** both `-appIcon` and `-sender` because
"macOS has no API to override a notification's icon; the icon always comes from
the app bundle".

So POPR brings its own bundle. `popr install` copies terminal-notifier's
`.app`, restamps `CFBundleIdentifier` to `be.tdries.popr`, sets the name and
`CFBundleIconFile` to POPR, drops in `assets/POPR.icns`, ad-hoc signs it
(`codesign --sign -`) and registers it with LaunchServices at
`~/Applications/POPR.app`. Notifications then post through
`$BUNDLE/Contents/MacOS/terminal-notifier`.

The reason this does not need an Apple Developer ID: Gatekeeper acts on the
**quarantine** attribute, which is applied to downloaded files. A bundle built on
the user's own machine has no quarantine attribute, so there is no warning to get
past. The source bundle is already ad-hoc signed, so re-signing ad-hoc after the
edits is consistent rather than a downgrade.

Consequences:

- The banner shows POPR and the confetti icon.
- macOS gives POPR its own row in System Settings › Notifications.
- `NSUserNotificationAlertStyle = alert` in the Info.plist makes macOS default
  the app to persistent Alerts rather than transient Banners, which is what
  "stays until you click it" means. **Verified on macOS 26.5**: POPR's row shows
  Meldingsstijl = Blijvend without the user touching anything. The user setting
  stays authoritative and can override it.
- The `.icns` is drawn on an ivory rounded body rather than transparent. Bare
  confetti has no mass and dissolves into a grey smudge at the 16 and 32 px
  sizes where an app icon actually lives, in the Settings list and elsewhere.
  The banner's `contentImage` keeps the transparent PNG, because it sits on the
  banner's own dark background.
- A terminal-notifier upgrade leaves the copy behind, so the bundle records
  `POPRBuiltFrom` and `popr doctor` flags a stale one.
- If the bundle cannot be built, POPR falls back to plain terminal-notifier and
  says so. Nothing breaks.

### 4.5 What macOS still will not allow

Asked and answered, so nobody relitigates it:

| Want | Verdict |
|---|---|
| Animated icon in the banner | No, and tested rather than assumed: an animated GIF passed as `-contentImage` is accepted, delivered, and rendered as its first frame only. |
| Removing the banner's left icon | No. It comes from the app bundle, and an `.icns` with every representation fully transparent renders as a **white square**. Verified on a bundle identifier macOS had never seen, so no icon cache was involved. |
| Any of it via a different notifier | No. `terminal-notifier`, `alerter`, `noti`, `osascript` all post through `UNUserNotificationCenter`; the banner is drawn by the OS, so the tool is irrelevant. |

All of which is why §4.6 stopped asking the notification system for anything.
| Control the banner layout | No. Five content slots (icon, name, title, subtitle, body) plus an optional right hand image, an action button and a reply field. Arrangement, type, colour, corner radius, position and the slide-in are the system's. |
| Force "stays until clicked" | Partly. It is the alert style, a per app user setting. The Info.plist key asks for the right default; the user can always override it. |
| Several notifications stacked | Yes, already. One `-group` per session id, so N live sessions give N banners. macOS collapses them into one stack while that app's "Group notifications" is set to Automatically; setting it to Off lists them individually. That is a user setting with no Info.plist equivalent. |

### 4.6 POPR draws its own banners

Given §4.5, the notification system cannot deliver the product. So POPR does not
use it. On every event it draws a window of its own:

- A non-activating `NSPanel` (style mask 128), so it takes a click without stealing focus from whatever you are typing in.
- 470 x 30, ivory `#F0EEE6`, corner radius half the height, hairline border. One line, grey `#6B6862` at 9.6pt, regular weight throughout.
- `NSStatusWindowLevel`, on every Space, and it stays until clicked. Clicking runs the same focus command the old notification did.
- Slots are claimed with `mkdir`, which is atomic, so two sessions finishing at the same instant cannot land on top of each other. A slot is released when its process exits, and reaped if that process died.

Native notifications are off by default (`native`), and `banner=false` falls back
to them if someone wants Notification Center history, Focus handling, or a
machine where `osascript` is unavailable.

**Two JXA traps**, both of which cost real time and are commented at the top of
`assets/banner.js` so they are not rediscovered:

1. `someNSColor.CGColor` returns a pointer owned by a temporary. The first use survives by luck and the *second* crashes the process with no error, no output, and no stack. Nothing in that file touches `CGColor`; `NSBox` takes `NSColor` directly.
2. `addSubview` on an `NSBox` goes into its `contentView`, which is inset by `contentViewMargins`. Every child then sits shifted by an amount that appears in no coordinate you wrote. The root is a plain `NSView` with the box as its first subview.

Title and status are budgeted rather than concatenated: on one fixed line a long
monorepo name would clip the status away, and the status is why the banner
exists. The banner is also announced to VoiceOver, since a borderless
non-activating panel is otherwise invisible to it, and replacing an accessible
notification with an inaccessible window would be a straight regression.

If the banner cannot be drawn, POPR falls back to a macOS notification. It
detects failure from the outcome string *and* from empty output, because a JXA
bridge failure kills the process without printing anything, which is exactly how
this project's two worst bugs presented.

Vertical placement of the text is a measured constant, not a derived one:
`NSTextField` does not put a single line where its `fittingSize` implies. It was
calibrated by rendering the same banner at a range of offsets, screenshotting,
and computing the ink centroid of each.

### 4.7 Confetti DNA

Every project gets its own mark and its own burst, both seeded from the project
name with FNV-1a and drawn procedurally. `acme-widgets` always throws the same
pieces the same way. Nothing is stored and no asset is generated.

Two rules keep the marks comparable rather than merely different:

- **Every colour, exactly once.** A mark carries all six brand colours; a burst carries all four explosion colours twice. Only the arrangement varies, so no project draws a dull one by chance.
- **Balanced by construction.** Two chips per row on a 3x3 grid, laid inside a margin. Balancing the rows up front beats correcting afterwards: a shift large enough to fix a lopsided draw is also large enough to push a chip out of the icon, and clamping that shift silently cancels it — which is exactly what happened on the first attempt.

The burst comes out of the mark, which is only possible because we draw the
banner. macOS never reveals where it puts its own, so there was nothing to aim at.

### 4.8 What a banner costs

Each open banner is an `osascript` process holding an AppKit window: about
**34 MB** of real memory (`phys_footprint`; RSS reads ~55 MB because it counts
shared framework pages once per process) and, since the run loop became event
driven, **no measurable CPU**.

A single long-lived helper owning every banner would cut the memory to 34 MB
regardless of how many are open. It is deliberately not built. Banners exist
between a turn ending and you clicking it, there is at most one per session, so
the common case is one or two; a helper would use the same memory there while
adding a lifecycle, an IPC path and a new way for notifications to stop arriving
entirely. Trading "always works" for "usually works, and uses less in a case
that rarely happens" is a bad deal for a tool whose whole value is reliability.

Worth revisiting if anyone routinely leaves five or more banners unclicked.

### 4.9 Sound

Three swells sharing one timbre, synthesized in `assets/make_sound.py` from the
standard library: G major and settled when a turn lands, rising and unresolved
when Claude needs you, minor and falling when it broke. macOS's fourteen system
sounds are all chimes or alerts, and a stock `Ping` next to a bespoke banner
would give the whole thing away.

## 5 · Configuration## 5 · Configuration

Three surfaces. Two of them are free, in that they are native features rather
than code POPR has to own.

1. **Claude Code plugin settings UI** — driven by the `userConfig` block in
   `.claude-plugin/plugin.json`. Marketplace users configure POPR in Claude's own
   settings screen. Zero code.
2. **`popr config`** — interactive `read` prompts writing
   `~/.config/popr/config.json`. For brew, curl and npm users.
3. **`POPR_*` environment variables** — for power users and CI.

Resolution order, first hit wins:

```
POPR_<KEY>  >  CLAUDE_PLUGIN_OPTION_<KEY>  >  ~/.config/popr/config.json  >  default
```

The config file is read once into a variable at startup and queried with `jq`. If
`jq` is missing the file is skipped and env plus defaults still work, so POPR
degrades rather than failing.

| Key | Default | Meaning |
|---|---|---|
| `sound_done` | `Glass` | macOS sound name, an absolute path to an audio file, or `none` |
| `sound_attention` | `Ping` | as above |
| `sound_error` | `Basso` | as above |
| `volume` | `1` | 0 to 1 |
| `speak` | `false` | also say the project name aloud |
| `quiet_when_focused` | `false` | skip the alert when the target app is already frontmost |
| `app` | autodetect | force the target app, e.g. `Cursor` |
| `icon` | bundled logo | path to a PNG, `app` for the host app icon, `none` to hide |
| `confetti` | `true` | the burst out of the banner's mark |
| `confetti_size` | `90` | how far it reaches, in pixels |
| `banner` | `true` | draw our own banner instead of a macOS notification |
| `banner_style` | `pill` | `pill` (ivory) or `glass` (blurred dark) |
| `banner_icon` | the project's own | a PNG to use instead of the generated mark |
| `banner_seconds` | `900` | backstop before a banner stops waiting for a click |
| `native` | `false` | also post a macOS notification, for the history |
| `font` | system | a family name, e.g. `Styrene A` |
| `summary_words` | `7` | words of status the banner shows |

## 6 · Logo

Direction C, "burst": a symmetric pixel confetti explosion from an orange core.
Chosen because it survives being 32 px in a banner and works as a square avatar
without an awkward empty corner.

Palette, Anthropic derived:

```
#D97757  primary orange      #6A9BCC  sky
#CC785C  book cloth          #BCD1CA  sage
#BF9C88  clay                #CBCADB  lavender
#F0EEE6  ivory ground        #191919  black ground
```

`assets/make_logo.py` holds the pixel grid as data and emits `logo.svg` plus PNGs
at 16/32/64/128/256/512. Python stdlib only: PNG bytes are written with `zlib` and
`struct`, so there is no Pillow, no Aseprite, and no build dependency. One source
of truth, regenerable at any size.

## 7 · Testing

`tests/test.sh` runs against `POPR_DRY_RUN=1`, asserts on stdout, and fires no
real notifications. Plain bash with `assert`, no framework.

Cases:

1. `stop` with `.last_assistant_message` produces a `✅` title carrying project and branch, message truncated to 140 chars.
2. `attention` with `.message` produces `⏳`.
3. `error` with `.error_type` produces `⚠️`.
4. An unknown mode exits 0 and prints nothing to the notifier.
5. Malformed stdin (not JSON, empty) exits 0.
6. Config precedence: env beats plugin option beats config file beats default.
7. Worktree: a `.git` file containing `gitdir:` resolves the project name to the main repo.
8. `clean()` strips a leading `-` so a message cannot be parsed as a `terminal-notifier` flag.

CI (`ci.yml`) runs on `macos-latest`: install `shellcheck jq terminal-notifier`,
`shellcheck bin/popr install.sh tests/test.sh`, then `tests/test.sh`.

## 8 · Release

`release.yml` fires on tag `v*`:

1. Build a tarball of the tree plus `Install POPR.command`, emit `sha256`.
2. `gh release create` with both.
3. If `TAP_TOKEN` is set: rewrite `Formula/popr.rb` in `tdries/homebrew-tap` with the new url and sha, commit, push.
4. If `NPM_TOKEN` is set: publish `packaging/npm` as `popr-cli`.

Steps 3 and 4 are conditional on the secret existing, so the first release
succeeds before the tap repo or the npm account exist.

## 9 · Out of scope

Deliberately not built, and not to be added without a new design:

- A menu bar app or any GUI beyond the two config surfaces above.
- Rebuilding Notification Center history, Focus awareness or Do Not Disturb on top of our own banners. `native=true` hands those back to macOS for anyone who wants them.
- `.pkg`, `.dmg`, `--cask`, Developer ID signing, notarization.
- A Notification Content Extension, and with it any animated or custom drawn banner.
- Windows or Linux support.
- Telemetry, analytics, crash reporting.
- Auto update.
- New notification features Butlr did not have (minimum turn duration, per project mute, notification history). This is a port and a repackage, not a feature release.

## 10 · Open items for the owner

These block the last mile of distribution and are not things POPR can do for itself:

1. ~~Create `tdries/homebrew-tap`.~~ Done.
2. ~~Set a tap credential.~~ Done, as a write deploy key scoped to the tap alone rather than a personal access token, stored as `TAP_DEPLOY_KEY`.
3. Claim an npm account and set `NPM_TOKEN` in repo secrets. Needs a browser login, so it cannot be automated.
4. Upload `assets/social-preview.png` under Settings › General › Social preview. GitHub exposes no API for this.
5. A real screenshot of a POPR banner would make the README hero far stronger than the logo PNG that ships in its place. Needs a human to trigger and capture one.
5. Decide whether to rename the repo to `tdries/popr`, which shortens the marketplace command from `tdries/td-claude-plugin-popr` to `tdries/popr`.

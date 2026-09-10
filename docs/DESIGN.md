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
- `NSUserNotificationAlertStyle = alert` in the Info.plist asks macOS to default
  the app to persistent Alerts rather than transient Banners, which is what
  "stays until you click it" means. It is a request, not a guarantee; the user
  setting is authoritative and the README says how to change it.
- A terminal-notifier upgrade leaves the copy behind, so the bundle records
  `POPRBuiltFrom` and `popr doctor` flags a stale one.
- If the bundle cannot be built, POPR falls back to plain terminal-notifier and
  says so. Nothing breaks.

### 4.5 What macOS still will not allow

Asked and answered, so nobody relitigates it:

| Want | Verdict |
|---|---|
| Animated icon in the banner | No. The banner renders one static image. A custom animated view needs a Notification Content Extension, which is an Xcode app target, only styles the *expanded* notification, and reintroduces signing. The logo is animated in the README instead. |
| Control the banner layout | No. Five content slots (icon, name, title, subtitle, body) plus an optional right hand image, an action button and a reply field. Arrangement, type, colour, corner radius, position and the slide-in are the system's. |
| Force "stays until clicked" | Partly. It is the alert style, a per app user setting. The Info.plist key asks for the right default; the user can always override it. |
| Several notifications stacked | Yes, already. One `-group` per session id, so N live sessions give N banners. macOS may still collapse them into one stack depending on that app's "Group notifications" setting. |

## 5 · Configuration

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
- `.pkg`, `.dmg`, `--cask`, Developer ID signing, notarization.
- A Notification Content Extension, and with it any animated or custom drawn banner.
- Windows or Linux support.
- Telemetry, analytics, crash reporting.
- Auto update.
- New notification features Butlr did not have (minimum turn duration, per project mute, notification history). This is a port and a repackage, not a feature release.

## 10 · Open items for the owner

These block the last mile of distribution and are not things POPR can do for itself:

1. Create `tdries/homebrew-tap`.
2. Claim an npm account and set `NPM_TOKEN` in repo secrets.
3. Set `TAP_TOKEN` (a PAT with repo scope on the tap) in repo secrets.
4. A real screenshot of a POPR banner would make the README hero far stronger than the logo PNG that ships in its place. Needs a human to trigger and capture one.
5. Decide whether to rename the repo to `tdries/popr`, which shortens the marketplace command from `tdries/td-claude-plugin-popr` to `tdries/popr`.

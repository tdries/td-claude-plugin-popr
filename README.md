<div align="center">

<img src="assets/logo-animated.svg" width="120" height="120" alt="POPR">

# POPR

**Clickable macOS notifications for Claude Code.**

A session finishes, wants a permission, or hits an error. You hear it, you see it,
and one click puts you back in the window it came from.

[![CI](https://github.com/tdries/td-claude-plugin-popr/actions/workflows/ci.yml/badge.svg)](https://github.com/tdries/td-claude-plugin-popr/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-D97757?style=flat-square)](LICENSE)
[![macOS](https://img.shields.io/badge/macOS-13%2B-191919?style=flat-square)](#requirements)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-CC785C?style=flat-square)](#install)

<img src="assets/banners.svg" width="620" alt="Three POPR notification banners stacked: a finished session, one waiting on a permission, and one that hit an API error.">

<sub>Illustration of the three banner types. Each carries POPR's own name and icon, not a generic terminal tool's.</sub>

</div>

---

## Why

You start something long in Claude Code, switch to another window, and lose the
thread. Either you babysit the session or you forget it for twenty minutes. POPR
is the smallest thing that fixes that: a sound, a banner that tells you *which*
project and *what* happened, and a click that takes you straight back.

Run five sessions at once and you get five banners, one per session, each
clicking through to its own window.

## What you get

| | |
|---|---|
| ✅ **Done** | Project, git branch, and a preview of Claude's last answer |
| ⏳ **Needs you** | Permission prompts, MCP input forms, background agents waiting |
| ⚠️ **Error** | The turn stopped on an API error, with the error type |
| 🖱 **One click back** | Reopens the exact editor window that session belongs to |
| 🧹 **Self cleaning** | A session's banner vanishes the moment you prompt it again |
| 🎊 **Its own identity** | POPR's name and confetti icon on the banner, and its own row in System Settings |
| 🎉 **A confetti burst** | An animated pixel burst in the corner when a turn lands, drawn by POPR itself |
| 🔒 **Nothing leaves** | No network calls, no telemetry. Ever. |

## Install

Pick **one**. Installing two ways would fire every notification twice, so POPR
detects that and refuses the second rather than let it happen.

<details open>
<summary><b>Claude Code plugin</b> — no terminal, recommended</summary>
<br>

```
/plugin marketplace add tdries/td-claude-plugin-popr
/plugin install popr@popr
```

Settings live in Claude Code's own plugin settings screen.

</details>

<details>
<summary><b>Homebrew</b></summary>
<br>

```bash
brew install tdries/tap/popr && popr install
```

</details>

<details>
<summary><b>curl</b></summary>
<br>

```bash
curl -fsSL https://raw.githubusercontent.com/tdries/td-claude-plugin-popr/main/install.sh | sh
```

</details>

<details>
<summary><b>npx</b></summary>
<br>

```bash
npx popr-cli install
```

</details>

<details>
<summary><b>Double click</b></summary>
<br>

Download the zip from [Releases](https://github.com/tdries/td-claude-plugin-popr/releases),
unzip, then **right click** `Install POPR.command` → **Open**.

The right click is not optional. A file downloaded through a browser is
quarantined by macOS, and POPR has no Developer ID certificate to clear that with,
so a plain double click gives you a warning and no way past. Right click → Open
gives you an **Open** button. Once, ever.

</details>

### Then, once

1. **System Settings › Notifications › POPR** → Allow notifications **on**.
   The style is already set to **Alerts** for you, which is what makes a banner wait
   for your click instead of vanishing after a few seconds. If you want several
   sessions listed one under the other rather than collapsed into a stack, set
   **Group notifications** to **Off** while you are there. Check no Focus mode is
   silencing it.
2. Reload your editor window (`Developer: Reload Window`), or `/reload-plugins` in a session.
3. `popr doctor`, then `popr test` or `/popr:test`.

## Configure

```bash
popr config     # interactive, writes ~/.config/popr/config.json
```

| Setting | Env var | Default | |
|---|---|---|---|
| Done sound | `POPR_SOUND_DONE` | `Glass` | a macOS sound name, an audio file path, or `none` |
| Needs input sound | `POPR_SOUND_ATTENTION` | `Ping` | |
| Error sound | `POPR_SOUND_ERROR` | `Basso` | |
| Volume | `POPR_VOLUME` | `1` | 0 to 1 |
| Say the project name | `POPR_SPEAK` | `false` | useful when you run many sessions |
| Quiet when the editor is in front | `POPR_QUIET_WHEN_FOCUSED` | `false` | |
| Force the target app | `POPR_APP` | autodetect | e.g. `Cursor` |
| Banner picture | `POPR_ICON` | POPR confetti | a PNG path, `app` for the editor icon, `none` |
| Confetti burst | `POPR_CONFETTI` | `true` | the animated burst when a turn finishes |
| Confetti size | `POPR_CONFETTI_SIZE` | `180` | pixels |

Sounds: Basso, Blow, Bottle, Frog, Funk, Glass, Hero, Morse, Ping, Pop, Purr,
Sosumi, Submarine, Tink.

Environment variables beat plugin options, which beat the config file, which beats
the defaults. Plugin users can set all of it in Claude Code's plugin settings.

## Commands

```bash
popr doctor        # dependencies, detected app, click action, hook and bundle status
popr test          # fire a test banner
popr config        # interactive settings
popr install       # build the bundle and register the hooks
popr uninstall     # remove both
```

## How it works

Four hooks call one bash script.

| Hook | Mode | |
|---|---|---|
| `Stop` | `stop` | ✅ banner with a preview of the answer |
| `Notification` | `attention` | ⏳ banner with Claude's own message |
| `StopFailure` | `error` | ⚠️ banner with the error type |
| `UserPromptSubmit` | `clear` | removes that session's stale banner |

**Finding your window.** POPR walks up the process tree until it hits the `.app`
bundle that launched Claude: VS Code, Cursor, Windsurf, VSCodium, Kiro, Trae,
Claude Desktop, or a terminal. For an editor the click runs
`open -a "<app>" "<project folder>"`, which raises the window that already has
that folder open. For anything else it activates the app.

**Never in your way.** All the slow work happens in a detached subshell and every
code path exits 0, so a hook cannot slow down or break your turn.

**The confetti.** macOS will not animate anything inside a notification: the
banner icon comes from the app bundle as a static `.icns`, and an animated GIF
handed over as the content image is shown as its first frame and nothing more.
Every notification tool on macOS posts through the same `UNUserNotificationCenter`,
so switching tools changes nothing — the banner is drawn by the OS.

So POPR does not ask the notification system for motion. On a finished turn it
draws its own window: borderless, transparent, click through, above everything,
gone in about a second. That window is entirely ours, so the animation is too.
It is a JXA script driven by `osascript`, which ships with macOS, so it needs no
Xcode and no extra dependency. A permission prompt or an API error gets no
confetti, because neither is worth celebrating. `POPR_CONFETTI=false` turns it off.

**Why it installs an app.** macOS takes a notification's icon and name from the
bundle that posts it, and offers no API to override either — `terminal-notifier`
removed its `-appIcon` and `-sender` flags for exactly this reason. So
`popr install` builds `~/Applications/POPR.app`: terminal-notifier's own bundle,
restamped with POPR's identity and icon, ad-hoc signed. Built on your machine it
carries no quarantine flag, so there is no Gatekeeper warning and no Apple
Developer account. That is what puts the confetti on the left and gives POPR its
own row in System Settings. If it cannot be built, POPR falls back to plain
terminal-notifier and tells you.

## Requirements

macOS 13 or later, [Claude Code](https://claude.com/claude-code), plus `jq` and
`terminal-notifier`, which every install path fetches for you through Homebrew.

## Limits

Honest ones, so nobody files them twice:

- **The banner cannot be animated, and its layout is not yours.** macOS draws it. You fill five slots: icon, name, title, subtitle, body, plus one optional static image, and an animated GIF in that slot renders as a still first frame. This is the OS, not the tool: every macOS notifier posts through the same framework. POPR's confetti sidesteps it by drawing a separate window, which is why the burst is animated and the banner icon is not.
- **"Stays until clicked" comes set up.** POPR's bundle declares the persistent Alerts style, so macOS defaults to it. You can still override it in System Settings, which always wins.
- **Stacking is partly macOS's call.** One banner per session is guaranteed. Whether several are listed separately or collapsed into one stack is POPR's "Group notifications" setting: set it to **Off** for a list. There is no way to declare that from the app.
- **The click focuses a window, not a tab.** With several sessions in one folder, the title tells you the project and the preview tells you the conversation.
- **`.code-workspace` spanning several folders** may open the project folder in a separate window.
- **macOS only**, by design.

Log: `~/Library/Logs/popr.log`

## Develop

```bash
tests/test.sh                                                   # 25 assertions, posts nothing
shellcheck bin/popr install.sh tests/test.sh "packaging/Install POPR.command"
python3 assets/make_logo.py --icns --gif                        # regenerate every logo form
```

Tests run under `POPR_DRY_RUN=1`, which prints what would be posted instead of
posting it. See [CONTRIBUTING.md](CONTRIBUTING.md).

[docs/DESIGN.md](docs/DESIGN.md) is the reasoning: why there is no `.app` to
download, what macOS refuses to allow, and what is deliberately out of scope.

## Project

[Contributing](CONTRIBUTING.md) ·
[Security](SECURITY.md) ·
[Code of conduct](CODE_OF_CONDUCT.md) ·
[Changelog](CHANGELOG.md) ·
[Design](docs/DESIGN.md)

POPR is a rename and repackage of Butlr, the same tool before it was fit to hand
to anyone else.

## License

MIT © [Tim Dries](https://github.com/tdries)

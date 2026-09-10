#!/bin/bash
# POPR tests. Everything runs under POPR_DRY_RUN=1, so no notification is ever
# posted, no sound is played and ~/.claude/settings.json is never touched.
#
#   tests/test.sh
set -u
export LC_ALL="${LC_ALL:-en_US.UTF-8}"  # so ${#msg} counts characters, not bytes

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POPR="$ROOT/bin/popr"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); printf '  ok   %s\n' "$1"; }
bad() {
    FAIL=$((FAIL + 1))
    printf '  FAIL %s\n' "$1"
    printf '       %s\n' "$2"
}

contains() { # label haystack needle
    case "$2" in
        *"$3"*) ok "$1" ;;
        *) bad "$1" "expected to contain: $3
       got: $2" ;;
    esac
}
absent() {
    case "$2" in
        *"$3"*) bad "$1" "should not contain: $3
       got: $2" ;;
        *) ok "$1" ;;
    esac
}

# Fixed host app and an empty config file, so results do not depend on which
# editor happens to be running the tests or on the developer's own settings.
export POPR_DRY_RUN=1
export POPR_APP=Cursor
export POPR_CONFIG="$TMP/config.json"

PROJ="$TMP/acme-widgets"
mkdir -p "$PROJ/.git"
printf 'ref: refs/heads/feature/tidy\n' >"$PROJ/.git/HEAD"

run() { # mode json
    printf '%s' "$2" | CLAUDE_PROJECT_DIR="$PROJ" "$POPR" "$1" 2>&1
}

echo "POPR tests"

# 1 · stop carries project, branch and the last thing Claude said
out="$(run stop '{"session_id":"s1","last_assistant_message":"Deployed to staging."}')"
contains "stop · title has project and branch" "$out" "title=✓ acme-widgets · feature/tidy"
contains "stop · subtitle names the app" "$out" "subtitle=Done in Cursor"
contains "stop · message is the status" "$out" "message=Deployed to staging"
contains "stop · click reopens the project" "$out" "click=open -a Cursor $PROJ"
contains "stop · banner grouped per session" "$out" "group=popr-s1"

# 2 · the banner gets a status, not an excerpt: first sentence, seven words at
#     most, and never an ellipsis, because it has exactly one line to live on
long="Deployed the release to staging and every one of the fourteen integration tests passed. Then I tidied up."
out="$(run stop "$(printf '{"session_id":"s1","last_assistant_message":"%s"}' "$long")")"
msg="${out#*message=}"
msg="${msg%%$'\t'*}"
msg="${msg#*· }"
words="$(printf '%s' "$msg" | wc -w | tr -d ' ')"
if [ "$words" -le 7 ]; then ok "stop · status is at most 7 words (got $words)"; else
    bad "stop · status is at most 7 words" "got $words: $msg"
fi
absent "stop · never trails off in an ellipsis" "$out" "…"
contains "stop · takes the first sentence, not the last" "$out" "Deployed the release"
out="$(POPR_SUMMARY_WORDS=3 run stop "$(printf '{"session_id":"s1","last_assistant_message":"%s"}' "$long")")"
contains "stop · word count is configurable" "$out" "message=Deployed the release	"

# 3 · empty summary still gives the user something to read
out="$(run stop '{"session_id":"s1"}')"
contains "stop · falls back when there is no summary" "$out" "message=Ready for your next prompt"

# 4 · attention relays Claude's own message
out="$(run attention '{"session_id":"s2","message":"Claude needs permission to run git push"}')"
contains "attention · title" "$out" "title=⋯ acme-widgets"
contains "attention · relays the message" "$out" "message=Claude needs permission to run git push"

# 5 · error names the failure
out="$(run error '{"session_id":"s3","error_type":"rate_limit_error"}')"
contains "error · title" "$out" "title=✕ acme-widgets"
contains "error · names the error type" "$out" "message=Claude hit an error: rate_limit_error"

# 6 · a message starting with "-" must not reach terminal-notifier as a flag,
#     where it would be parsed as an option instead of text
out="$(run attention '{"session_id":"s4","message":"-title pwned -execute rm -rf /"}')"
absent "clean · leading dash stripped" "$out" "message=-title"
contains "clean · text survives" "$out" "pwned"

# 7 · a hook must never break the turn
out="$(run bogus-mode '{}')"; rc=$?
if [ $rc -eq 0 ]; then ok "unknown mode exits 0"; else bad "unknown mode exits 0" "exit $rc"; fi
absent "unknown mode posts nothing" "$out" "NOTIFY"

out="$(printf 'not json at all' | CLAUDE_PROJECT_DIR="$PROJ" "$POPR" stop 2>&1)"; rc=$?
if [ $rc -eq 0 ]; then ok "malformed stdin exits 0"; else bad "malformed stdin exits 0" "exit $rc"; fi
contains "malformed stdin still notifies" "$out" "NOTIFY"

# 8 · settings precedence: env > config file > default
printf '{"app":"Windsurf","icon":"none"}\n' >"$POPR_CONFIG"
out="$(POPR_APP="" run stop '{"session_id":"s5"}')"
contains "config file · app is read" "$out" "click=open -a Windsurf"
out="$(run stop '{"session_id":"s5"}')" # POPR_APP=Cursor still exported
contains "env beats config file" "$out" "click=open -a Cursor"
: >"$POPR_CONFIG"

# 8b · the right-hand picture is empty by default. macOS always draws the app
#      bundle's icon on the LEFT, so a second copy on the right was the same mark
#      twice. An explicit path still puts one back.
out="$(run stop '{"session_id":"s9"}')"
contains "icon · no right-hand picture by default" "$out" "icon=	"
printf 'x' >"$TMP/mine.png"
out="$(POPR_ICON="$TMP/mine.png" run stop '{"session_id":"s9"}')"
contains "icon · an explicit path is used" "$out" "icon=$TMP/mine.png"
out="$(POPR_ICON=none run stop '{"session_id":"s9"}')"
contains "icon · none stays empty" "$out" "icon=	"
out="$(POPR_ICON=/does/not/exist.png run stop '{"session_id":"s9"}')"
contains "icon · a missing file falls back to empty, never a broken path" "$out" "icon=	"

# 9 · in a git worktree the project name is the main repo, not the worktree dir
WT="$TMP/wt-scratch"
mkdir -p "$PROJ/.git/worktrees/scratch" "$WT"
printf 'ref: refs/heads/hotfix\n' >"$PROJ/.git/worktrees/scratch/HEAD"
printf 'gitdir: %s/.git/worktrees/scratch\n' "$PROJ" >"$WT/.git"
out="$(printf '%s' '{"session_id":"s6"}' | CLAUDE_PROJECT_DIR="$WT" "$POPR" stop 2>&1)"
contains "worktree · resolves to the main repo and its branch" "$out" "title=✓ acme-widgets · hotfix"

# 10 · banners post through POPR's own bundle when it has been built, which is
#      what puts POPR's name and icon on the left instead of terminal-notifier's
out="$(POPR_BUNDLE="$TMP/absent.app" run stop '{"session_id":"s7"}')"
contains "unbranded when no bundle is present" "$out" "branded=0"

FAKE="$TMP/POPR.app/Contents/MacOS"
mkdir -p "$FAKE"
printf '#!/bin/sh\nexit 0\n' >"$FAKE/terminal-notifier"
chmod +x "$FAKE/terminal-notifier"
out="$(POPR_BUNDLE="$TMP/POPR.app" run stop '{"session_id":"s7"}')"
contains "branded once the bundle exists" "$out" "branded=1"

# 11 · the confetti overlay fires when a turn finishes, and only then. A
#      permission prompt or an API error is not something to throw a party over.
out="$(run stop '{"session_id":"s8"}')"
contains "banner · drawn by POPR, not macOS" "$out" "style=pill"
contains "banner · one line of status, prefixed by where" "$out" "message=Ready for your next prompt"

# 11b · POPR must return immediately, with the banner left running detached.
#       This is the hook contract: a banner that waits for a click would
#       otherwise hold the calling shell open for as long as it is on screen,
#       and in a hook that means Claude waiting. Redirecting the command inside
#       the subshell is not enough; the subshell itself must give up the stdio
#       it inherited. Timed end to end rather than asserted about the source.
start="$(date +%s)"
POPR_DRY_RUN="" POPR_CONFETTI=false POPR_BANNER_SECONDS=1 \
    CLAUDE_PROJECT_DIR="$PROJ" "$POPR" test >/dev/null 2>&1
elapsed=$(($(date +%s) - start))
if [ "$elapsed" -le 3 ]; then ok "returns at once, banner runs detached (${elapsed}s)"; else
    bad "returns at once, banner runs detached" "took ${elapsed}s; the subshell is holding stdio"
fi

# 12 · the generated marks and bursts obey their rules for every project name
if command -v osascript >/dev/null 2>&1; then
    res="$(osascript -l JavaScript "$ROOT/tests/banner-rules.js" "$ROOT/assets/banner.js" 2>&1)"
    case "$res" in
        ok*) ok "banner rules · $res" ;;
        *) bad "banner rules" "$res" ;;
    esac
fi

# 13 · version matches the packaged manifests
v="$("$POPR" version)"
for m in "$ROOT/.claude-plugin/plugin.json" "$ROOT/packaging/npm/package.json"; do
    [ -f "$m" ] || continue
    mv="$(jq -r .version "$m")"
    if [ "$v" = "$mv" ]; then
        ok "version matches $(basename "$(dirname "$m")")/$(basename "$m")"
    else
        bad "version matches $m" "popr says $v, manifest says $mv"
    fi
done

echo
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]

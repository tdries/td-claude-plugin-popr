#!/bin/bash
# POPR installer · macOS only
#
#   curl -fsSL https://raw.githubusercontent.com/tdries/td-claude-plugin-popr/main/install.sh | sh
#
# or, from a clone or an unpacked release:
#
#   ./install.sh
#
# Installs the package to ~/.local/share/popr, links ~/.local/bin/popr, then
# hands over to `popr install` to register the Claude Code hooks.
set -euo pipefail

REPO="tdries/td-claude-plugin-popr"
PREFIX="${POPR_PREFIX:-$HOME/.local}"
DEST="$PREFIX/share/popr"
BINDIR="$PREFIX/bin"

if [ "$(uname)" != Darwin ]; then
    echo "POPR only runs on macOS." >&2
    exit 1
fi
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

need() {
    command -v "$1" >/dev/null 2>&1 && return 0
    if command -v brew >/dev/null 2>&1; then
        echo "→ installing $1 with Homebrew"
        brew install "$1"
    else
        echo "✗ $1 is missing and Homebrew is not installed. Get it at https://brew.sh, then rerun." >&2
        exit 1
    fi
}
need terminal-notifier
need jq

# Piped from curl there is no local tree, so fetch one. From a clone or an
# unpacked release, use what is already here.
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$HERE" ] && [ -f "$HERE/bin/popr" ]; then
    SRC="$HERE"
    echo "→ installing from $SRC"
else
    SRC="$(mktemp -d)"
    trap 'rm -rf "$SRC"' EXIT
    echo "→ downloading $REPO"
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/main" |
        tar -xz -C "$SRC" --strip-components=1
fi

echo "→ installing to $DEST"
mkdir -p "$BINDIR" "$(dirname "$DEST")"
rm -rf "$DEST"
cp -R "$SRC" "$DEST"
rm -rf "$DEST/.git"
chmod +x "$DEST/bin/popr"
ln -sf "$DEST/bin/popr" "$BINDIR/popr"

case ":$PATH:" in
    *":$BINDIR:"*) ;;
    *)
        echo
        echo "⚠ $BINDIR is not on your PATH. Add this to your shell profile:"
        echo "    export PATH=\"$BINDIR:\$PATH\""
        echo
        ;;
esac

"$BINDIR/popr" install "$@"

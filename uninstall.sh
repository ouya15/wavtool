#!/usr/bin/env bash
# wavtool uninstaller — removes the private python env and the CLI wrapper.
# It does NOT touch your data or shell history; leftovers are listed at the end.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[wavtool] removing private python env: $HOME/.wavtool"
rm -rf "$HOME/.wavtool"

echo "[wavtool] removing CLI wrapper: $HOME/.local/bin/wavtool"
rm -f "$HOME/.local/bin/wavtool"

echo ""
echo "[wavtool] done. the following are left untouched on purpose:"
echo "  1) WAV files produced by 'pack'  (your data)"
echo "  2) shell history (~/.zsh_history) may reference wavtool/git commands"
echo "  3) if installed via npm:  npm cache clean --force"
echo "  4) this directory itself:  rm -rf \"$DIR\""

#!/usr/bin/env bash
# wavtool installer/updater — idempotent; no archive files are ever created.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY3="$(command -v python3 || true)"
if [ -z "$PY3" ]; then
  echo "[wavtool] Python 3.10+ required. macOS: xcode-select --install  (or: brew install python3)"
  exit 1
fi

WV_HOME="$HOME/.wavtool"
if [ ! -x "$WV_HOME/venv/bin/python3" ]; then
  echo "[wavtool] preparing private Python environment (one-time, needs network)..."
  mkdir -p "$WV_HOME"
  "$PY3" -m venv "$WV_HOME/venv"
fi
PIP_NO_CACHE_DIR=1 "$WV_HOME/venv/bin/python3" -m pip install --quiet --disable-pip-version-check --no-cache-dir numpy reedsolo zstandard
echo "[wavtool] python env ready."

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/wavtool" <<EOF
#!/usr/bin/env bash
PY="$WV_HOME/venv/bin/python3"
case "\${1:-}" in
  pack) shift; exec "\$PY" "$DIR/python/tx_pack.py" "\$@" ;;
  --version|-v) echo "wavtool 2.0.0"; ;;
  *) echo "usage: wavtool pack <dir> <out.wav>"; exit 2 ;;
esac
EOF
chmod +x "$BIN_DIR/wavtool"

echo "[wavtool] installed/updated: $BIN_DIR/wavtool  (repo: $DIR)"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "  note: add to PATH ->  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc" ;;
esac

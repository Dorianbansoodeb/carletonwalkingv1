#!/usr/bin/env bash
# Install Python deps (OSMnx) for building the MARS drive graph.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$ROOT/.venv"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 not found. Install Python 3.10+ and retry." >&2
  exit 1
fi

echo "Creating virtualenv at $VENV"
python3 -m venv "$VENV"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Installed. Next steps:"
echo "  source $VENV/bin/activate"
echo "  python $SCRIPT_DIR/build_drive_graph.py"
echo "  python $SCRIPT_DIR/build_resources.py"

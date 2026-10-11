#!/data/data/com.termux/files/usr/bin/bash

REPO_URL="https://raw.githubusercontent.com/ONLINE-SERVER/sxg-bypass/main"
WORKDIR="$HOME/.sxg_bypass"

mkdir -p "$WORKDIR"
cd "$WORKDIR"

curl -fsSL "$REPO_URL/SXG_BYPASS.py" -o SXG_BYPASS.py || {
    echo "[X] Download failed!"
    exit 1
}

python -c "import pytz, gmalg, Crypto, zstandard" 2>/dev/null || {
    pip install --quiet pytz gmalg pycryptodome zstandard
}

python SXG_BYPASS.py "$@"

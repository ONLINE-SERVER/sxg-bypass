#!/data/data/com.termux/files/usr/bin/bash

REPO_URL="https://github.com/ONLINE-SERVER/sxg-bypass"
WORKDIR="$HOME/.sxg_bypass"
BIN="$PREFIX/bin/sxgbypass"

echo "[*] Installing SXG BYPASS..."

pkg update -y >/dev/null 2>&1 || true
pkg install -y python clang git >/dev/null 2>&1 || true
pip install --quiet pytz gmalg pycryptodome zstandard >/dev/null 2>&1 || true

mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "[*] Downloading SXG_BYPASS.py..."
curl -fsSL "$REPO_URL/SXG_BYPASS.py" -o SXG_BYPASS.py

cat > "$BIN" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
cd "$WORKDIR"
python SXG_BYPASS.py "\$@"
EOF
chmod +x "$BIN"

echo ""
echo "[+] Installation Complete!"
echo "[+] Ab kabhi bhi bas ye command chalao:"
echo ""
echo "    sxgbypass"
echo ""

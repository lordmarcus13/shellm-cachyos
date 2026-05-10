#!/usr/bin/env bash
set -e

echo "================================================="
echo "  sheLLm CachyCore HyperState - Installer"
echo "================================================="

INSTALL_DIR="$HOME/.shellm"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/lordmarcus13/shellm-cachyos.git"

# 1. Ensure dependencies
echo "[+] Checking dependencies (git, python3)..."
if ! command -v git &> /dev/null; then
    echo "[-] Git is required but not found. Exiting."
    exit 1
fi
if ! command -v python3 &> /dev/null; then
    echo "[-] Python3 is required but not found. Exiting."
    exit 1
fi

# 2. Clone or Update
if [ -d "$INSTALL_DIR" ]; then
    echo "[+] Existing installation found at $INSTALL_DIR. Updating..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "[+] Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Setup Python Virtual Environment
echo "[+] Setting up isolated Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
echo "[+] Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# 4. Create executable wrapper
echo "[+] Creating global executable wrapper..."
mkdir -p "$BIN_DIR"
WRAPPER="$BIN_DIR/shellm"

cat << 'EOF' > "$WRAPPER"
#!/usr/bin/env bash
INSTALL_DIR="$HOME/.shellm"
cd "$INSTALL_DIR" || { echo "[-] Installation directory missing."; exit 1; }

echo "[sheLLm] Syncing with neural matrix (Checking for updates)..."
# Auto-update silently
git pull origin main --quiet

source venv/bin/activate
# Execute the hyperstate
exec python run.py "$@"
EOF

chmod +x "$WRAPPER"

echo "================================================="
echo "[+] Installation Complete!"
echo "[+] Executable installed at: $WRAPPER"
echo "[+] Ensure $BIN_DIR is in your PATH."
echo "[+] Run 'shellm' to initiate the CachyCore HyperState."
echo "================================================="

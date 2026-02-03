#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SERVE_DIR="$HOME/kindle_drop"
EBOOK_CONVERT="/Applications/calibre.app/Contents/MacOS/ebook-convert"

echo "=== Kindle Drop Setup ==="
echo

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 not found."
    echo "  Fix: Run 'xcode-select --install' to get Apple's Python 3."
    exit 1
fi
echo "✓ Python 3 found: $(python3 --version)"

# 2. Check Calibre
if [ ! -f "$EBOOK_CONVERT" ]; then
    echo "ERROR: Calibre not found at $EBOOK_CONVERT"
    echo "  Fix: Install Calibre with 'brew install --cask calibre'"
    echo "       or download from https://calibre-ebook.com/download_osx"
    exit 1
fi
echo "✓ Calibre found"

# 3. Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
echo "✓ Virtual environment ready"

# 4. Install dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed"

# 5. Create serve directory
mkdir -p "$SERVE_DIR"
echo "✓ Serve directory: $SERVE_DIR"

# 6. Create desktop launcher
LAUNCHER="$HOME/Desktop/Kindle Drop.command"
cat > "$LAUNCHER" << LAUNCHER_EOF
#!/bin/bash
cd "$SCRIPT_DIR"
"$VENV_DIR/bin/python" "$SCRIPT_DIR/kindle_drop.py"
LAUNCHER_EOF

chmod +x "$LAUNCHER"
echo "✓ Desktop launcher created"

echo
echo "Done! Double-click 'Kindle Drop' on your Desktop to launch."

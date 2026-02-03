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

# 6. Create .app bundle on Desktop
APP_DIR="$HOME/Desktop/Kindle Drop.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

# 6a. Generate icon PNG with Pillow, then convert to .icns with sips
ICON_PNG="$RESOURCES_DIR/app.png"
ICON_ICNS="$RESOURCES_DIR/app.icns"

"$VENV_DIR/bin/python" - "$ICON_PNG" << 'ICON_EOF'
import sys
from PIL import Image, ImageDraw, ImageFont

size = 512
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Rounded-rect background
r = 80
draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(30, 60, 120))

# "KD" text centred
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 220)
except OSError:
    font = ImageFont.load_default()
bbox = draw.textbbox((0, 0), "KD", font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), "KD", fill="white", font=font)

img.save(sys.argv[1])
ICON_EOF

sips -s format icns "$ICON_PNG" --out "$ICON_ICNS" &>/dev/null
rm -f "$ICON_PNG"
echo "✓ App icon generated"

# 6b. Write Info.plist
cat > "$CONTENTS_DIR/Info.plist" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Kindle Drop</string>
    <key>CFBundleIdentifier</key>
    <string>com.kindledrop.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>CFBundleIconFile</key>
    <string>app</string>
</dict>
</plist>
PLIST_EOF

# 6c. Write launch script
cat > "$MACOS_DIR/launch" << LAUNCH_EOF
#!/bin/bash
cd "$SCRIPT_DIR"
"$VENV_DIR/bin/python" "$SCRIPT_DIR/kindle_drop.py"
LAUNCH_EOF

chmod +x "$MACOS_DIR/launch"
echo "✓ Desktop app bundle created"

echo
echo "Done! Double-click 'Kindle Drop' on your Desktop to launch."

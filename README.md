# Kindle Drop

Drop EPUBs → convert to AZW3 → serve over Wi-Fi → download on Kindle.

## Prerequisites

- **macOS** with Python 3 (`xcode-select --install` if missing)
- **Calibre**: `brew install --cask calibre` or [calibre-ebook.com](https://calibre-ebook.com/download_osx)
- Kindle and Mac on the same Wi-Fi network

## Setup (one time)

```bash
./setup.sh
```

Creates a virtual environment, installs dependencies, and puts a **Kindle Drop** launcher on your Desktop.

## Usage

1. Double-click **Kindle Drop** on your Desktop
2. Drag EPUB files onto the window (or click "Choose files")
3. Type the displayed URL (e.g. `http://192.168.1.42:8000`) into your Kindle's browser
4. Tap the `.azw3` file to download
5. Close the window when done — the server stops automatically

## Files

| File | Purpose |
|------|---------|
| `kindle_drop.py` | App: GUI + conversion + file server |
| `setup.sh` | One-time setup script |
| `requirements.txt` | Python dependencies (`pywebview`) |

Converted files are served from `~/kindle_drop`.

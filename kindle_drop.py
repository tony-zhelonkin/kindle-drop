#!/usr/bin/env python3
"""Kindle Drop — Drop EPUBs, convert to AZW3, serve over Wi-Fi for Kindle download."""

import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path

import webview

# --- Constants ---
SERVE_DIR = Path.home() / "kindle_drop"
EBOOK_CONVERT = "/Applications/calibre.app/Contents/MacOS/ebook-convert"
PORT_START = 8000


def get_local_ip():
    """Get this machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start_server(serve_dir, port_start=PORT_START):
    """Start an HTTP file server in a daemon thread. Returns (server, actual_port)."""
    serve_dir.mkdir(parents=True, exist_ok=True)

    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
        *args, directory=str(serve_dir), **kwargs
    )

    for port in range(port_start, port_start + 100):
        try:
            server = http.server.HTTPServer(("0.0.0.0", port), handler)
            break
        except OSError:
            continue
    else:
        # Let OS pick a free port
        server = http.server.HTTPServer(("0.0.0.0", 0), handler)
        port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


class Api:
    """Bridge between the JS UI and Python backend."""

    def __init__(self, window_ref):
        self._window_ref = window_ref
        self._calibre_ok = os.path.isfile(EBOOK_CONVERT)

    def get_status(self):
        """Return initial status info for the UI."""
        return {"calibre_ok": self._calibre_ok, "url": SERVER_URL}

    def choose_and_process(self):
        """Open a native file picker and process selected files."""
        window = self._window_ref()
        if window is None:
            return
        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=("EPUB files (*.epub)", "All files (*.*)"),
        )
        if result:
            self.process_files(list(result))

    def process_files(self, paths):
        """Convert EPUBs to AZW3, copy other files to serve directory."""
        if not paths:
            return
        for filepath in paths:
            filepath = filepath.strip()
            if not filepath or not os.path.isfile(filepath):
                self._log(f"Skipped (not found): {os.path.basename(filepath)}")
                continue

            name = os.path.basename(filepath)
            _, ext = os.path.splitext(name)
            ext = ext.lower()

            if ext == ".epub":
                self._convert_epub(filepath, name)
            else:
                dest = SERVE_DIR / name
                shutil.copy2(filepath, dest)
                self._log(f"Copied: {name}")

    def _convert_epub(self, filepath, name):
        """Convert a single EPUB to AZW3 using Calibre's ebook-convert."""
        if not self._calibre_ok:
            self._log(f"ERROR: Calibre not found — cannot convert {name}")
            return

        stem = os.path.splitext(name)[0]
        out_path = SERVE_DIR / f"{stem}.azw3"
        self._log(f"Converting: {name} ...")

        try:
            result = subprocess.run(
                [EBOOK_CONVERT, filepath, str(out_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                self._log(f"Done: {stem}.azw3")
            else:
                err = result.stderr.strip().split("\n")[-1] if result.stderr else "unknown error"
                self._log(f"FAILED: {name} — {err}")
        except subprocess.TimeoutExpired:
            self._log(f"FAILED: {name} — conversion timed out")
        except Exception as e:
            self._log(f"FAILED: {name} — {e}")

    def _log(self, msg):
        """Send a log message to the JS UI."""
        window = self._window_ref()
        if window:
            safe = json.dumps(msg)
            window.evaluate_js(f"addLog({safe})")


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    background: #1a1a2e; color: #e0e0e0;
    display: flex; flex-direction: column; height: 100vh;
    padding: 20px; user-select: none;
  }
  h1 { font-size: 20px; text-align: center; margin-bottom: 6px; color: #fff; }
  .url-bar {
    text-align: center; font-size: 22px; font-weight: 600;
    color: #00d4ff; margin-bottom: 16px; letter-spacing: 0.5px;
  }
  .url-bar small { display: block; font-size: 12px; color: #888; font-weight: 400; }
  #drop-zone {
    flex: 1; min-height: 120px;
    border: 2px dashed #444; border-radius: 12px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    transition: border-color 0.2s, background 0.2s;
    cursor: pointer; margin-bottom: 12px;
  }
  #drop-zone.hover { border-color: #00d4ff; background: rgba(0,212,255,0.06); }
  #drop-zone .icon { font-size: 40px; margin-bottom: 8px; }
  #drop-zone .label { font-size: 15px; color: #aaa; }
  #drop-zone .sublabel { font-size: 12px; color: #666; margin-top: 4px; }
  button {
    display: block; margin: 0 auto 14px;
    padding: 8px 24px; font-size: 14px;
    background: #16213e; color: #00d4ff; border: 1px solid #00d4ff;
    border-radius: 6px; cursor: pointer;
  }
  button:hover { background: #0f3460; }
  #log {
    height: 130px; overflow-y: auto; font-size: 13px;
    font-family: "SF Mono", Menlo, monospace;
    background: #0f0f23; border-radius: 8px; padding: 10px;
    line-height: 1.5;
  }
  #log .entry { color: #8892b0; }
  #log .entry.done { color: #64ffda; }
  #log .entry.error { color: #ff6b6b; }
  .error-banner {
    background: #ff6b6b22; color: #ff6b6b; padding: 10px;
    border-radius: 8px; text-align: center; margin-bottom: 12px; font-size: 13px;
  }
</style>
</head>
<body>

<h1>Kindle Drop</h1>
<div class="url-bar" id="url-bar">loading...</div>

<div id="error-banner-slot"></div>

<div id="drop-zone">
  <div class="icon">📥</div>
  <div class="label">Drop EPUB files here</div>
  <div class="sublabel">or click "Choose files" below</div>
</div>

<button id="choose-btn" onclick="pywebview.api.choose_and_process()">Choose files</button>

<div id="log"></div>

<script>
function addLog(msg) {
  const log = document.getElementById('log');
  const div = document.createElement('div');
  div.className = 'entry';
  if (msg.startsWith('Done:') || msg.startsWith('Copied:')) div.className += ' done';
  if (msg.startsWith('ERROR') || msg.startsWith('FAILED')) div.className += ' error';
  div.textContent = msg;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

// Drag and drop
const dz = document.getElementById('drop-zone');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('hover'); });
dz.addEventListener('dragleave', e => { e.preventDefault(); dz.classList.remove('hover'); });
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.classList.remove('hover');

  // Try to get file paths from the drop event
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    // In pywebview, dropped files may have .path available
    const paths = [];
    for (let i = 0; i < files.length; i++) {
      // webkitRelativePath or name — pywebview on macOS provides full path via File.path
      if (files[i].path) {
        paths.push(files[i].path);
      }
    }
    if (paths.length > 0) {
      pywebview.api.process_files(paths);
    } else {
      addLog("Drag-and-drop paths not available — use 'Choose files' button instead.");
    }
  }
});

// Also allow clicking the drop zone
dz.addEventListener('click', () => pywebview.api.choose_and_process());

// On load, get status
window.addEventListener('pywebviewready', () => {
  pywebview.api.get_status().then(status => {
    document.getElementById('url-bar').innerHTML =
      status.url + '<small>Type this URL in your Kindle browser</small>';
    if (!status.calibre_ok) {
      document.getElementById('error-banner-slot').innerHTML =
        '<div class="error-banner">Calibre not found at expected path. ' +
        'Install it: <b>brew install --cask calibre</b></div>';
    }
  });
});
</script>
</body>
</html>
"""


def main():
    SERVE_DIR.mkdir(parents=True, exist_ok=True)

    server, port = start_server(SERVE_DIR)
    ip = get_local_ip()

    global SERVER_URL
    SERVER_URL = f"http://{ip}:{port}"

    # We need a way to pass the window reference to the Api after creation.
    # Use a mutable container.
    window_holder = [None]
    api = Api(lambda: window_holder[0])

    window = webview.create_window(
        "Kindle Drop",
        html=HTML,
        js_api=api,
        width=480,
        height=540,
        resizable=True,
    )
    window_holder[0] = window

    webview.start()  # Blocks until window is closed

    server.shutdown()


if __name__ == "__main__":
    main()

import re
import time
import urllib.request
import urllib.error
from base64 import b64encode

from flask import Flask, jsonify, render_template, Response

# ── Config ─────────────────────────────────────────────────────
CAMERA_HOST = "http://192.168.0.132"
CAMERA_USER = "admin"
CAMERA_PASS = "lounge-writer-ipod"
SERVER_PORT = 8080

app = Flask(__name__)

# ── Camera request helper ──────────────────────────────────────
def camera_get(path, timeout=5):
    """Make an authenticated GET request to the camera. Returns bytes."""
    url = CAMERA_HOST + path
    credentials = b64encode(f"{CAMERA_USER}:{CAMERA_PASS}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {credentials}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

def camera_get_text(path, timeout=5):
    return camera_get(path, timeout).decode("utf-8", errors="replace")

# ── Parsers ────────────────────────────────────────────────────
def parse_js_vars(text):
    """Parse 'var key="value";' lines into a dict."""
    return dict(re.findall(r'var (\w+)="([^"]*)"', text))

def parse_state_js(text):
    """
    Parse the camera's state.js file into structured data.

    Example content:
      mac_str='... (3) ';
      state_str='V3.3.0.7 [X] on Publishing ... rtmp://... (up from 02/24 13:06:43) with Audio (1)';
      url_str='rtmp://a.rtmp.youtube.com/live2/XXXX';
      up_time=1772001014;
    """
    result = {
        "streaming": False,
        "viewer_count": 0,
        "url": "",
        "uptime_seconds": None,
        "state_raw": text.strip(),
    }

    # url_str
    m = re.search(r"url_str='([^']*)'", text)
    if m:
        result["url"] = m.group(1)

    # streaming: "Publishing" appears in state_str when live
    result["streaming"] = "Publishing" in text

    # viewer count: mac_str ends with "(N) "
    m = re.search(r"\((\d+)\)\s*'", text)
    if m:
        result["viewer_count"] = int(m.group(1))

    # up_time: unix timestamp of when the current publish session started
    m = re.search(r"up_time=(\d+)", text)
    if m:
        up_time = int(m.group(1))
        result["uptime_seconds"] = max(0, int(time.time()) - up_time)

    return result

def parse_syslog(text):
    """
    Parse syslog.txt lines into [{time, event}].

    Example line: [2026_02_24 17:43:45] ircut: display switch(color -> blackwhite).
    """
    lines = []
    for match in re.finditer(
        r'\[(\d{4}_\d{2}_\d{2} \d{2}:\d{2}:\d{2})\]\s*(.+)', text
    ):
        # "2026_02_24 17:43:45" → "2026-02-24 17:43:45"
        timestamp = match.group(1).replace("_", "-", 2)
        lines.append({"time": timestamp, "event": match.group(2).strip()})
    return lines

# ── Routes ─────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/snapshot")
def api_snapshot():
    """Proxy the live snapshot JPEG from the camera."""
    try:
        data = camera_get("/tmpfs/snap.jpg", timeout=8)
        return Response(data, mimetype="image/jpeg")
    except Exception as e:
        return Response(status=503)

@app.route("/api/status")
def api_status():
    """Return current streaming status parsed from state.js."""
    try:
        text = camera_get_text("/tmpfs/state.js")
        return jsonify(parse_state_js(text))
    except Exception as e:
        return jsonify({"streaming": False, "error": str(e)}), 503

@app.route("/api/info")
def api_info():
    """Return device info parsed from getserverinfo CGI."""
    try:
        text = camera_get_text("/cgi-bin/hi3510/param.cgi?cmd=getserverinfo")
        v = parse_js_vars(text)
        return jsonify({
            "model":       v.get("model", ""),
            "firmware":    v.get("softVersion", ""),
            "startdate":   v.get("startdate", ""),
            "sd_free_mb":  round(int(v.get("sdfreespace", 0)) / 1024 / 1024),
            "sd_total_mb": round(int(v.get("sdtotalspace", 0)) / 1024 / 1024),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 503

@app.route("/api/syslog")
def api_syslog():
    """Return parsed syslog entries."""
    try:
        text = camera_get_text("/tmpfs/syslog.txt")
        return jsonify({"lines": parse_syslog(text)})
    except Exception as e:
        return jsonify({"lines": [], "error": str(e)}), 503

@app.route("/api/reboot", methods=["POST"])
def api_reboot():
    """Send the reboot command to the camera."""
    try:
        camera_get("/cgi-bin/hi3510/param.cgi?cmd=sysreboot", timeout=5)
        return jsonify({"ok": True})
    except Exception:
        # The camera often drops the connection as it reboots — that's expected.
        return jsonify({"ok": True})

# ── Entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Bird cam dashboard running at http://localhost:{SERVER_PORT}")
    app.run(host="0.0.0.0", port=SERVER_PORT, debug=False)

# Seattle Bird Buddies — Camera Dashboard

## Project structure

```
birdcam/
├── server.py           # Flask app and camera proxy
├── requirements.txt    # Python dependencies (Flask + python-dotenv)
├── .env                # Your credentials and config — never committed
├── .env.example        # Template showing required variables — committed
├── templates/
│   └── index.html      # The dashboard UI
├── CAMERA_API.md       # Full camera API reference
└── README.md           # This file
```

---

## Information Sources

| Feature | Source | Method |
|---|---|---|
| Live feed | `/tmpfs/snap.jpg` | Browser reloads the JPEG every 5s with a cache-busting timestamp |
| LIVE badge + viewer count | `/tmpfs/state.js` | Polled every 15s, parsed with regex |
| Stream uptime | `/tmpfs/state.js` | Contains a Unix timestamp; subtracted from now |
| Recent events | `/tmpfs/syslog.txt` | Polled every 15s, last 6 lines displayed |
| System info | CGI `cmd=getserverinfo` | Polled every 60s |
| Reboot | CGI `cmd=sysreboot` | POST to `/api/reboot`, then polls snapshot until camera returns |

The Flask server acts as a proxy between the browser and the camera. Camera credentials are loaded from `.env` at startup and never exposed to the browser.

---

## Prerequisites

- Python 3.8 or later
- The camera reachable on your local network at `192.168.0.132`

---

## Local setup

```bash
cd ~/development/birdcam

# Create the virtual environment (once)
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies (once)
pip install -r requirements.txt

# Set up your config (once)
cp .env.example .env
# Edit .env and fill in your camera credentials

# Run the server
python3 server.py
```

Open `http://localhost:8080` in your browser.

---

## Deployment (home server)

### 1. Copy files to the server

Run this from your Mac, replacing `myserver` with your server's hostname or IP:

```bash
scp -r ~/development/birdcam myserver:~/birdcam
```

### 2. Set up the environment

```bash
ssh myserver
cd ~/birdcam
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in your camera credentials
nano .env
```

### 3. Test manually

```bash
python3 server.py
```

Open `http://myserver:8080` from your phone or another browser on the network to confirm it works, then `Ctrl+C` to stop it.

### 4. Install as a systemd service

This makes the dashboard start automatically on boot and restart if it crashes.

Create the service file:

```bash
sudo nano /etc/systemd/system/birdcam.service
```

Replace `YOUR_USERNAME` with your server's username:

```ini
[Unit]
Description=Bird Cam Dashboard
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/birdcam
ExecStart=/home/YOUR_USERNAME/birdcam/venv/bin/python server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable birdcam
sudo systemctl start birdcam
```

Check it's running:

```bash
sudo systemctl status birdcam
```

The dashboard will now be available at `http://myserver:8080` permanently.

For logs:

```bash
journalctl -u birdcam -f
```

---

## Camera API

See `CAMERA_API.md` for the full reference including all known endpoints, response formats, and how they were discovered.

To reboot the camera directly from the terminal (sources credentials from `.env`):

```bash
source .env && curl -u "$CAMERA_USER:$CAMERA_PASS" "$CAMERA_HOST/cgi-bin/hi3510/param.cgi?cmd=sysreboot"
```

Endpoints used by this app:

| Endpoint | Used for |
|---|---|
| `GET /tmpfs/snap.jpg` | Live snapshot |
| `GET /tmpfs/auto.jpg` | Sub-stream snapshot (800×600) |
| `GET /tmpfs/state.js` | Streaming status, viewer count, uptime |
| `GET /tmpfs/syslog.txt` | Event log |
| `GET /cgi-bin/hi3510/param.cgi?cmd=getserverinfo` | Device info, SD card status |
| `GET /cgi-bin/hi3510/param.cgi?cmd=sysreboot` | Reboot the camera |

---

## Venv quick reference

```bash
# Create
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

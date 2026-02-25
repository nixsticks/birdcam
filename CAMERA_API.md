# Seattle Bird Buddies — Camera API Reference

This document covers the HTTP API of the IP camera at `192.168.0.132`.
All requests require **HTTP Basic Auth**: username `admin`, password in your secrets store.

---

## How This Was Discovered

The camera runs a **HiSilicon Hi3510** SoC — a common embedded Linux chipset used in many IP camera brands. The discovery process was:

1. **Read the HTML source** of the main page (`http://192.168.0.132/`). It referenced `cgi-bin/hi3510/param.cgi?cmd=getlanguage` directly in a `<script>` tag. This revealed the entire API pattern: one CGI endpoint with a `cmd=` query parameter.
2. **Recognized the chipset** from the path `hi3510/`. This family of cameras uses a consistent CGI interface across manufacturers, making it possible to guess command names.
3. **Guessed `cmd=` values** by following the naming convention: `get<noun>attr` or `get<noun>`. Tried ~50 candidates, ~15 returned valid data.
4. **Found the snapshot** at `/tmpfs/snap.jpg` — `tmpfs` is a standard Linux temporary filesystem. Embedded cameras almost always write their live snapshot there. The directory listing at `/tmpfs/` was also open, revealing the full filesystem layout.

---

## Device Info

| Field           | Value                          |
|-----------------|--------------------------------|
| Name            | IPCAM (OSD label: "seattle bird buddies") |
| Model           | C6F0SoZ3N0PdL2                 |
| Hardware        | V1.0.0.1                       |
| Firmware        | V19.1.61.16.12-20210226        |
| Web UI          | V3.0.7.1                       |
| MAC Address     | 98:03:CF:B8:31:00              |
| Network         | Wireless LAN (Wi-Fi)           |
| IP              | 192.168.0.132 (DHCP)           |
| Gateway         | 192.168.0.1                    |

**SD Card:**
- Status: Ready
- Total: ~119 MB
- Free: ~119 MB

---

## Authentication

All endpoints use **HTTP Basic Authentication**.

```
Username: admin
Password: <see your secrets store>
```

Pass credentials via header or URL:

```bash
curl -u admin:PASSWORD http://192.168.0.132/<endpoint>
```

---

## Snapshots (Still Images)

Two resolutions are always available as JPEG files served directly from the camera's tmpfs:

| URL                              | Resolution  | Description              |
|----------------------------------|-------------|--------------------------|
| `GET /tmpfs/snap.jpg`            | 2560×1920   | Main stream snapshot     |
| `GET /tmpfs/auto.jpg`            | 800×600     | Sub stream snapshot      |

These files are updated continuously by the camera. They are **not** generated on-request — you're reading the most recently written frame.

```bash
# Grab the current hi-res frame
curl -u admin:PASSWORD http://192.168.0.132/tmpfs/snap.jpg -o frame.jpg
```

> **Note:** The camera mounts with flip and mirror both enabled (image is rotated 180°). The camera is physically mounted upside-down. If you process frames programmatically, apply a 180° rotation to correct orientation.

---

## Video Streams

### RTSP (recommended for playback/recording)

The camera exposes two RTSP streams on port `554`:

| Stream     | URL                                                      | Resolution  | Bitrate   |
|------------|----------------------------------------------------------|-------------|-----------|
| Main       | `rtsp://admin:PASSWORD@192.168.0.132:554/11`             | 2560×1920   | 6144 kbps |
| Sub        | `rtsp://admin:PASSWORD@192.168.0.132:554/12`             | 800×600     | 512 kbps  |

Both streams run at **15 fps** with a GOP of 60 frames, VBR encoding (brmode=1).

```bash
# Play main stream
ffplay rtsp://admin:PASSWORD@192.168.0.132:554/11

# Record sub stream to file
ffmpeg -i rtsp://admin:PASSWORD@192.168.0.132:554/12 -c copy output.mp4
```

### RTMP

The camera also exposes RTMP on port `1935`. The camera currently uses this port to push a live stream to YouTube (see Streaming Status below).

### ONVIF

ONVIF is enabled on port `8080`. This allows integration with NVR software (Home Assistant, Blue Iris, iSpy, etc.).

```
ONVIF endpoint: http://192.168.0.132:8080/onvif/device_service
Auth required: No (ov_authflag=0)
```

---

## CGI Parameter API

**Base URL:** `GET /cgi-bin/hi3510/param.cgi?cmd=<command>[&-param=value]`

Responses are JavaScript variable assignments (e.g. `var key="value";`), intended to be eval'd by the browser. For programmatic use, parse them as key-value pairs.

Setter commands use the same endpoint with `cmd=set<noun>attr` and additional `-<field>=<value>` query parameters.

### Device / Server Info

**`cmd=getserverinfo`** — General device info

```js
var model="C6F0SoZ3N0PdL2";
var hardVersion="V1.0.0.1";
var softVersion="V19.1.61.16.12-20210226";
var webVersion="V3.0.7.1";
var name="IPCAM";
var startdate="2026-02-24 12:06:50";   // last boot time
var sdshow="0";
var sdstatus="Ready";
var sdfreespace="125141248";            // bytes
var sdtotalspace="125143104";           // bytes
```

**`cmd=getlanguage`** — UI language code

```js
var lancode="1";   // 1 = English
```

### Network

**`cmd=getnetattr`** — Network configuration

```js
var dhcpflag="on";
var ip="192.168.0.132";
var netmask="255.255.255.0";
var gateway="192.168.0.1";
var dnsstat="1";
var fdnsip="192.168.0.1";
var sdnsip="";
var macaddress="98:03:CF:B8:31:00";
var networktype="Wireless LAN";
```

**`cmd=gethttpport`**

```js
var httpport="80";
```

**`cmd=getrtmpattr`**

```js
var rtmpport="1935";
```

**`cmd=getrtspport`**

```js
var rtspport="554";
var rtpport="6600";
```

**`cmd=getonvifattr`** — ONVIF settings

```js
var ov_enable="1";
var ov_port="8080";
var ov_authflag="0";      // 0 = no auth required
var ov_forbitset="3";
var ov_subchn="12";       // ONVIF sub-stream channel
var ov_snapchn="12";      // ONVIF snapshot channel
var ov_nvctype="0";
```

**`cmd=getupnpattr`** — UPnP (disabled)

```js
var upm_enable="0";
```

**`cmd=getntpattr`** — NTP time sync

```js
var ntpenable="1";
var ntpserver="ntp.main";
var ntpinterval="1";      // sync interval in hours
```

### Video / Encoding

**`cmd=getvideoattr`** — Video mode

```js
var videomode="101";
var vinorm="P";       // PAL
var profile="0";
var maxchn="2";       // 2 channels: main + sub
var wdrmode="0";
```

**`cmd=getvencattr&-chn=1`** — Main stream encoding (channel 1)

```js
var bps_1="6144";         // bitrate kbps
var fps_1="15";
var gop_1="60";
var brmode_1="1";         // 1 = VBR
var imagegrade_1="1";
var width_1="2560";
var height_1="1920";
```

**`cmd=getvencattr&-chn=2`** — Sub stream encoding (channel 2)

```js
var bps_2="512";
var fps_2="15";
var gop_2="60";
var brmode_2="1";
var imagegrade_2="1";
var width_2="800";
var height_2="600";
```

### Image / Camera

**`cmd=getimageattr`** — Image processing settings

```js
var display_mode="0";
var brightness="50";
var saturation="0";
var sharpness="65";
var contrast="50";
var hue="50";
var wdr="on";             // Wide Dynamic Range enabled
var wdrvalue="15";
var night="on";           // night mode (IR cut filter)
var shutter="2000";
var flash_shutter="14";
var flip="on";            // image flipped vertically
var mirror="on";          // image mirrored horizontally
var gc="63";
var ae="2";
var targety="60";
var noise="0";
var gamma="1";
var aemode="0";
var imgmode="1";
```

> **flip + mirror both on** = camera is physically mounted upside-down, the firmware corrects the orientation.

### PIR Sensor

**`cmd=getpirattr`** — Passive infrared motion sensor

```js
var pir_enable="0";   // PIR disabled
var pir_flag="1";
```

### Cloud / P2P

**`cmd=getcloudattr`** — Cloud connectivity

```js
var cloud_flag="1";
var cloud_enable="0";   // cloud push disabled
```

### FTP Upload

**`cmd=getftpattr`** — FTP push settings (currently unconfigured)

```js
var ft_server="";
var ft_port="21";
var ft_username="";
var ft_password="";
var ft_mode="1";
var ft_dirname="./";
var ft_autocreatedir="1";
```

---

## Live Streaming Status

The camera maintains a real-time status file at `/tmpfs/state.js`. This is the most useful file for monitoring the live stream health.

**`GET /tmpfs/state.js`**

```js
mac_str='<wifi_mac> / password:<p2p_password> (<viewer_count>)';
state_str='<firmware_ver> [<flags>] on Publishing ... <rtmp_url> (up from MM/DD HH:MM:SS) with Audio (1)';
url_str='<rtmp_url>';
up_time=<unix_timestamp>;
ipc_ty=3;
hls_str=' [SD-TS] ';
```

| Field        | Description |
|--------------|-------------|
| `mac_str`    | WiFi MAC address and P2P password + current viewer count |
| `state_str`  | Human-readable status: firmware version, current RTMP destination, uptime since |
| `url_str`    | The RTMP URL currently being pushed to (contains the stream key — treat as secret) |
| `up_time`    | Unix timestamp of current publish session start |
| `ipc_ty`     | Internal camera type flag |
| `hls_str`    | HLS transport format indicator |

**Example parsed status:** Streaming live to YouTube, up since 13:06, with audio, 3 viewers.

> **Security note:** `state.js` contains the live RTMP stream key in plaintext. Do not expose this file publicly.

---

## System Log

**`GET /tmpfs/syslog.txt`** — Recent system events

Contains timestamped entries for:
- NTP time syncs (hourly)
- HTTP/RTSP stream login/logout events
- IR cut filter switches (color → black/white at dusk, reverse at dawn)

```
[2026_02_24 12:07:10] update time[ntp]: 2026-02-24 12:07:10
[2026_02_24 12:07:15] user() login for http stream.
[2026_02_24 13:06:37] user() login for rtsp stream.
[2026_02_24 17:43:45] ircut: display switch(color -> blackwhite).
```

The IR cut switch entries are useful for knowing when dawn/dusk occurred.

---

## Tmpfs Directory

The entire `/tmpfs/` directory is publicly accessible (with auth). Key files:

| File               | Description |
|--------------------|-------------|
| `snap.jpg`         | Current main stream frame (2560×1920) |
| `auto.jpg`         | Current sub stream frame (800×600) |
| `state.js`         | Live streaming status (see above) |
| `syslog.txt`       | System event log |
| `play.conf`        | Encoded streaming configuration (base64) |
| `sensor.conf`      | Image sensor ID (`sensor=35`) |
| `wpa.conf`         | WiFi WPA configuration |
| `wifi.mac`         | WiFi MAC address |
| `push.uid`         | Camera P2P UID (e.g. `SSAC-409436-BEDFF`) |
| `push.ip`          | Current P2P server IP |
| `server.ip`        | Main relay server IP |
| `ip0` / `ip1`      | Resolved IPs for relay servers |
| `netflag.dat`      | Network status flag |
| `sd/`              | SD card recording directory |

---

## Setter Commands

Write operations follow the same pattern with `set` instead of `get`, plus `-<field>=<value>` parameters. **These modify camera settings — use with care.**

```bash
# Example: set brightness to 60
curl -u admin:PASSWORD \
  "http://192.168.0.132/cgi-bin/hi3510/param.cgi?cmd=setimageattr&-brightness=60"
```

Known setter commands (corresponding to the getters above):
- `setimageattr` — image/camera settings
- `setnetattr` — network settings
- `setntpattr` — NTP settings
- `setlanguage&-lancode=<code>` — UI language

---

## Quick Reference

```bash
export CAM="http://192.168.0.132"
export AUTH="admin:PASSWORD"

# Current snapshot (hi-res)
curl -u $AUTH $CAM/tmpfs/snap.jpg -o snap.jpg

# Current snapshot (low-res)
curl -u $AUTH $CAM/tmpfs/auto.jpg -o auto.jpg

# Streaming status
curl -u $AUTH $CAM/tmpfs/state.js

# System log
curl -u $AUTH $CAM/tmpfs/syslog.txt

# Device info
curl -u $AUTH "$CAM/cgi-bin/hi3510/param.cgi?cmd=getserverinfo"

# Network info
curl -u $AUTH "$CAM/cgi-bin/hi3510/param.cgi?cmd=getnetattr"

# Play main RTSP stream
ffplay rtsp://admin:PASSWORD@192.168.0.132:554/11

# Play sub RTSP stream
ffplay rtsp://admin:PASSWORD@192.168.0.132:554/12
```

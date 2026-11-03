#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p /data /home/baguette/.config
Xvfb :99 -screen 0 1280x900x24 -nolisten tcp -noreset > /data/xvfb.log 2>&1 &
for attempt in $(seq 1 40); do
    xdpyinfo -display :99 >/dev/null 2>&1 && break
    sleep .25
done
openbox > /data/openbox.log 2>&1 &
if [[ ! -s /data/desktop-password ]]; then
    /opt/baguette/.venv/bin/python -c 'import secrets,string; print("".join(secrets.choice(string.ascii_letters+string.digits) for _ in range(8)))' > /data/desktop-password
fi
x11vnc -storepasswd "$(cat /data/desktop-password)" /data/desktop-password.hash >/dev/null 2>&1
x11vnc -display :99 -localhost -rfbauth /data/desktop-password.hash -forever -shared -rfbport 5900 > /data/desktop.log 2>&1 &
websockify --web=/usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900 > /data/web-desktop.log 2>&1 &
# The official client writes only its own Docker volume, not an existing host account.
wechat_bin=$(command -v wechat || command -v weixin || true)
if [[ -x /opt/wechat/wechat ]]; then wechat_bin=/opt/wechat/wechat; fi
if [[ -z "$wechat_bin" ]]; then echo 'Official WeChat executable not found'; exit 1; fi
# dbus-run-session scopes the client and visual runner to this desktop.
exec dbus-run-session -- bash -c '
    /opt/baguette/.venv/bin/python /opt/baguette/linux/wechat_client.py "$1" > /data/wechat.log 2>&1 &
    exec /opt/baguette/.venv/bin/python /opt/baguette/linux/supervisor.py
' baguette-session "$wechat_bin"

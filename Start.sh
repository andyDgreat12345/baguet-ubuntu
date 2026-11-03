#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ "$(uname -s)" != Linux ]]; then
    echo 'This launcher is for Ubuntu Linux. The existing macOS VM guide remains in docs/INSTALL.en.md.' >&2
    exit 1
fi
if ! command -v docker >/dev/null; then
    echo 'Install Docker Engine + Compose first: https://docs.docker.com/engine/install/ubuntu/' >&2
    echo 'Then run bash Start.sh again. / 安装 Docker 和 Compose 后重新运行。' >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo 'Docker is not accessible. Start Docker and use an account allowed to run it (or sudo bash Start.sh).' >&2
    exit 1
fi
docker compose version >/dev/null
docker compose up -d --build
printf '\nBaguet setup / 设置: http://127.0.0.1:8766\nWeChat / 微信: http://127.0.0.1:8766/desktop.html\n'
printf 'First build downloads the official client, Python dependencies and models.\n'
if command -v xdg-open >/dev/null; then xdg-open http://127.0.0.1:8766 >/dev/null 2>&1 || true; fi

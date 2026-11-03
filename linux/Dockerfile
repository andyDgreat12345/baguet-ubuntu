FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git python3 python3-venv python3-dev build-essential \
    xvfb openbox x11vnc novnc websockify xdotool wmctrl xclip x11-utils lsof dbus-x11 tini \
    fonts-noto-cjk libgl1 libglib2.0-0 libgtk-3-0 libnss3 libxss1 libgbm1 libasound2t64 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 \
    libxcb-xkb1 libxkbcommon-x11-0 libatomic1 libatk-bridge2.0-0 libcups2 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
ARG TARGETARCH
RUN case "$TARGETARCH" in amd64) arch=x86_64;; arm64) arch=arm64;; *) exit 1;; esac; \
    curl -fL --retry 3 "https://dldir1v6.qq.com/weixin/Universal/Linux/WeChatLinux_${arch}.deb" -o /tmp/wechat.deb \
    && apt-get update && apt-get install -y /tmp/wechat.deb \
    && dpkg-query -W -f='${Version}\n' wechat > /etc/baguette-wechat-version \
    && rm -f /tmp/wechat.deb && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/baguette
COPY requirements.txt requirements-brain.txt UPSTREAMS.lock.json /tmp/baguette-build/
COPY linux/requirements.txt /tmp/baguette-build/linux-requirements.txt
COPY linux/fetch_locked.py /tmp/baguette-build/fetch_locked.py
RUN python3 -m venv .venv \
    && .venv/bin/pip install --upgrade pip \
    && .venv/bin/python /tmp/baguette-build/fetch_locked.py /tmp/baguette-build/UPSTREAMS.lock.json /opt/baguette-upstreams
RUN --mount=type=cache,target=/root/.cache/pip .venv/bin/pip install \
        -r /tmp/baguette-build/requirements.txt -r /tmp/baguette-build/requirements-brain.txt \
    && .venv/bin/pip install /opt/baguette-upstreams/astrbot \
    && .venv/bin/pip install -r /opt/baguette-upstreams/livingmemory/requirements.txt -r /opt/baguette-upstreams/stealer/requirements.txt
# Only WeChat-AI's visual components are imported; database/key scanners are not started.
RUN --mount=type=cache,target=/root/.cache/pip .venv/bin/pip install torch==2.9.0 torchvision==0.24.0 --index-url https://download.pytorch.org/whl/cpu \
    && .venv/bin/pip install -r /tmp/baguette-build/linux-requirements.txt
# RapidOCR's pinned default cache is inside site-packages. Populate it before
# dropping privileges so first use never attempts writes to a root-owned package.
RUN .venv/bin/python -c 'from rapidocr import RapidOCR; RapidOCR()'
# The official client dynamically loads these without declaring all of them in
# its Debian dependencies. Missing libpulse causes a crash before login.
RUN apt-get update && apt-get install -y --no-install-recommends libegl1 libegl-mesa0 libgles2 libpulse0 \
    && rm -rf /var/lib/apt/lists/*
COPY . /opt/baguette
RUN mkdir -p /data /home/baguette \
    && useradd --uid 10001 --home-dir /home/baguette --shell /bin/bash baguette \
    && chown -R 10001:10001 /data /home/baguette \
    && chmod +x linux/entrypoint.sh
ENV DISPLAY=:99 BAGUETTE_CONTAINER=1 BAGUETTE_RUNTIME=/data \
    HOME=/home/baguette \
    BAGUETTE_UPSTREAMS=/opt/baguette-upstreams \
    PYTHONPATH=/opt/baguette/app:/opt/baguette-upstreams/linux_visual/src \
    QT_SCALE_FACTOR=1 QT_AUTO_SCREEN_SCALE_FACTOR=0 QT_FONT_DPI=96 \
    QT_QPA_PLATFORM=xcb LANG=C.UTF-8 LC_ALL=C.UTF-8
USER 10001:10001
VOLUME ["/data", "/home/baguette"]
EXPOSE 8766 6080
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/baguette/linux/entrypoint.sh"]

> **Ubuntu 24.04 local package (developer preview):** run `bash Start.sh`, add your DeepSeek key, log into your chosen WeChat account and bind one conversation in the browser. No spare account is required. See the [Ubuntu guide](docs/UBUNTU.en.md). Existing macOS VM instructions remain available; Linux Favorites sending awaits calibration.

[Download the Ubuntu preview](https://github.com/andyDgreat12345/baguet-ubuntu/releases) · [简体中文](README.md) · [Validation](VALIDATION.json)

# Baguette 🥖 — Big Fat Fish for WeChat

[简体中文](README.md) · [Installation](docs/INSTALL.en.md) · [Agent guide](AGENTS.md)

A visual companion for an ordinary WeChat account. The Ubuntu 24.04 package runs official Linux WeChat in its own Docker desktop; the original macOS VM path is also retained. It reads visible chat screenshots, replies through DeepSeek, and operates WeChat's actual UI. Favorites sending is calibrated only on the original macOS path.

**Developer alpha.** This is a visual/UI bridge, not a peer-to-peer model or an official WeChat API. Content comes from screenshots; platform UI APIs locate windows and operate controls. WeChat databases and process injection are not used.

The reasoning and memory runtime is the original [AstrBot](https://github.com/AstrBotDevs/AstrBot) with [LivingMemory](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory). The original [Stealer](https://github.com/nagatoquin33/astrbot_plugin_stealer) classifies incoming sticker crops; [Dafeiyu](https://github.com/whyever77/dafeiyu-astrbot) supplies the persona reference. See [attribution and pinned revisions](docs/ATTRIBUTION.md).

## Start here

On Ubuntu 24.04, install Docker Engine and Compose v2, unpack the complete package and run:

```bash
bash Start.sh
```

Follow the [Ubuntu guide](docs/UBUNTU.en.md): enter a DeepSeek key, prepare models, log into your chosen account, preview/bind one conversation, then start. Plan for 16 GB RAM and 40 GB free disk as an initial trial budget, not a measured minimum. API usage may cost money. First run downloads dependencies and local models.

The clean Ubuntu ARM64 image build, setup panel and official WeChat login screen have been checked. **Logged-in Linux message reading, image interpretation and real delivery are still pending acceptance.** See [validation details](VALIDATION.json). Existing Apple Silicon users can use the [macOS VM guide](docs/INSTALL.en.md).

## Capabilities and boundaries

- Scoped persona, long-term memory, retrieval and group-language learning through the QQ framework.
- Incoming visible images get local descriptions, emotion and usage labels; recent captions survive into a following “interpret this sticker” request.
- Favorites navigation, reverse ordering, scrolling, thumbnail matching and one-click sending after calibration.
- Groups are read; replies require addressing/mentions or a bounded conversational follow-up.
- A visible outgoing bubble is checked; this does not prove recipient delivery.
- Visible windows/current animation frames only. Full history, every group, complete GIFs, voice/video and restart-after-host-reboot coverage remain incomplete.
- Optional same-login-session controller supervision preserves run/pause intent. Ambiguous sends remain blocked.

No credentials, private conversations, learned memories, VM disks, model weights, or personal sticker collections are shipped. API usage may cost money. The public release includes configuration examples and import/calibration instructions rather than someone else's live account.

## Contribute

Read [CONTRIBUTING](CONTRIBUTING.md), [security](SECURITY.md), [privacy](docs/PRIVACY.md) and [roadmap](docs/ROADMAP.md). Reproducible, redacted compatibility reports and installation receipts are especially useful. If the project helps, a star makes it easier for others to find.

AGPL-3.0; upstream licenses are preserved. Not affiliated with Tencent/WeChat.

# Changelog

## 0.2.0-ubuntu-preview.2

- Make the expired-binding-preview regression test deterministic on freshly booted CI runners. Runtime binding checks are unchanged.
- Keep the original preview tag immutable; refresh the downloadable source package and validation evidence.

## 0.2.0-ubuntu-preview.1

- Keep a direct sticker request attached to its actual speaker when other group messages arrive; recognize common Chinese and English commands and omit sticker-only text prefaces.
- On the calibrated macOS path, explicitly requested stickers can follow verified text despite other speakers, while manual own-account replies still cancel stale actions. Linux Favorites sending remains unavailable.

- Docker-hosted official Linux WeChat with a browser desktop, including headless Ubuntu 24.04 servers.
- Bilingual API-key/personality setup, explicit account/current-chat preview, one selected conversation and pause/start controls.
- No spare-account requirement; independent account and conversation namespaces.
- Reuses original AstrBot/LivingMemory/Stealer and pinned WeChat-AI visual components.
- Current short-reply, native reasoning and group-authority guards carried forward.
- Visible-image recognition wired to the original QQ pipeline; Linux Favorites sending remains explicitly unavailable pending calibration.
- Source/unit checks, image build, actual login and real deliveries are tracked separately in VALIDATION.json.

## 0.1.0-alpha.1

Initial public integration source, bilingual setup documentation and pinned QQ upstream provenance. Includes scoped visual text/media ingest, original memory/sticker framework bridge, Favorites scrolling and thumbnail validation, recent image continuity for follow-up questions, busy-group response handling, explicit delivery uncertainty, and optional same-session controller supervision.

This is an alpha source release. The development VM has live validation; a clean second-machine install and host reboot recovery are not accepted as complete.

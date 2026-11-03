# 致谢与来源 / Attribution

The WeChat bridge and adapters are integration work. The original QQ components deserve credit for the memory, reflection and sticker processing used here. Upstream source is fetched at pinned revisions, not bundled runtime data.

This separate Ubuntu package continues the [Baguette WeChat integration](https://github.com/andyDgreat12345/baguette-wechat). Its earlier macOS path and notices are retained; Ubuntu-specific setup and validation are documented separately.

| Project | Pinned revision | License | Reuse |
|---|---|---|---|
| [astrbot](https://github.com/AstrBotDevs/AstrBot) | `abf683071952375ec36baa4cad6b6f3d9c9bb03f` | AGPL-3.0 | Actual native message, LLM, tool and conversation pipeline |
| [livingmemory](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory) | `a1e9c20a8c5fab93d6143f51be26fb1bbf8143ec` | AGPL-3.0 | Original long-term storage, retrieval and reflection plugin |
| [stealer](https://github.com/nagatoquin33/astrbot_plugin_stealer) | `758f94a5b0848c8723a56d20af3da4b8ef3c4e61` | AGPL-3.0 | Original image/sticker classifier, emotion/scenario extraction and local library |
| [dafeiyu](https://github.com/whyever77/dafeiyu-astrbot) | `fd220118f7a23a26a4ccfeb8eb69a2c93a80f226` | MIT | Unmodified original persona + clearly separate WeChat capability overlay; full QQ device/browser tools are not ported |

Tart is a separately installed virtualization product under its own [license](https://tart.run/licensing/). The guest RPC helper comes from [openai/tart-guest-agent](https://github.com/openai/tart-guest-agent); its binary is fetched separately with a pinned SHA-256. macOS, WeChat, Ollama model weights and user-provided stickers are not relicensed by this repository. See upstream notices in `licenses/`.

`resources/persona/dafeiyu-original.md` is copied without modification under the upstream MIT license. The overlay states only actually available WeChat capabilities. AstrBot/LivingMemory/Stealer license texts are preserved. The project uses AGPL-3.0 for its integration code. Nothing here claims to be an official Tencent product.

The branding SVG is original vector artwork created for this repository. No private chat screenshots or personal sticker guide PDF are included. Meme/image ownership was not verified for the development account's collection, so those files remain local.


## Ubuntu visual bridge

[ChisBread/wechat-ai](https://github.com/ChisBread/wechat-ai), GPL-3.0-or-later, commit 638e98e51fd373f11d62965a41bccb603d63954c, supplies the Linux screenshot/YOLO, RapidOCR, layout reader and enabled Send-button detection. Its attribution to [weixin-omni/omni-bot-sdk-oss](https://github.com/weixin-omni/omni-bot-sdk-oss) is preserved. This package does not start WeChat-AI's database/key-scanning services. The pinned checkout, original LICENSE and CREDITS remain in the built image. Docker desktop transport uses Ubuntu packages Xvfb/Openbox/x11vnc/noVNC/websockify; local inference uses the official Ollama image. These retain their respective licenses. The official Tencent client is downloaded during installation, not bundled in this source ZIP.

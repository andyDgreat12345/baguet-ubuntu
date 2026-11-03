# Ubuntu 24.04 local package

Run `bash Start.sh` from the unpacked root after installing [Docker Engine and Compose](https://docs.docker.com/engine/install/ubuntu/). The package builds an official Linux WeChat desktop inside Docker, a browser setup UI, the original QQ memory/vision pipeline, and local Ollama. No Mac, macOS VM, iPad or attached monitor is required. Use any WeChat account you control and can actually log into.

**Developer preview:** the clean ARM64 image build, QR login screen, setup API, VNC authentication and worker recovery have been checked. Logged-in Linux replies, image interpretation, full model preparation and long-term operation still need end-to-end acceptance; amd64 has not been built on real hardware. See [VALIDATION.json](../VALIDATION.json).

1. Open <http://127.0.0.1:8766>. Save your DeepSeek API key, bot mention name and character notes. Select a model available on your own DeepSeek account.
2. Press **Prepare**. The first preparation downloads local embedding/vision models, sets up original AstrBot/LivingMemory/Stealer, installs the persona through AstrBot's API and checks DeepSeek without sending a WeChat message.
3. Open <http://127.0.0.1:8766/desktop.html>. Scan/approve login on your phone. Open the intended group or private conversation. Keep light theme and 100% scaling.
4. Press **Read current chat** in setup. Check the account preview and chat title, enter the visible account name, choose group/private, and confirm **Bind**.
5. Press **Start**. The current viewport becomes a quiet baseline. Send a new message from another account and inspect the resulting outgoing bubble and actual receiving account.

To change chats, pause, open the other chat in WeChat, refresh the preview and bind again. One selected chat is automated at a time. Account namespaces isolate both local consumed messages and QQ memory. A selected private conversation does not grant the correspondent administrator authority. Group members cannot change configuration or turn the character into a code/essay assistant.

Default group policy replies to mentions/direct calls; selective participation is an optional setting. Replies remain short. Original LivingMemory handles memory and five-round reflection; this is not model-weight training.

For a remote server, forward both local ports with `ssh -L 8766:127.0.0.1:8766 -L 6080:127.0.0.1:6080 user@server`, then use the same localhost URLs. The default Compose publishes only on host loopback. Closing the browser or your iPad does not stop the server.

Plan for 16 GB+ RAM and 40 GB+ free disk for an initial trial; 32 GB is preferable for local vision. These are planning budgets, not measured minima. CPU inference is supported but first image analysis can be slow. Internet access is needed for the initial image/build/model downloads and ongoing DeepSeek requests. This ZIP contains source and launchers, not an offline image or model weights.

`docker compose stop` preserves configuration, memory, WeChat login data and models. `docker compose up -d` starts again. Do not delete volumes without your own backup. Setup pause state is saved. The supervisor restarts only its owned worker; uncertain sends, changed bindings and expired logins still require inspection. After a client/container restart, you may need phone login approval and a new binding. Never blindly retry an uncertain send.

**Linux coverage:** visible text and image crops; the original QQ Stealer and local Qwen interpret visible images. OCR can fail, and offscreen messages, full animations, voice/video are not guaranteed. **Linux Favorites sending is not calibrated in this package**: sticker actions are explicitly rejected and short text remains available. Existing macOS Favorites code is retained separately. See [full Chinese guide](UBUNTU.zh-CN.md) for operational details and upstream citations.

No developer credentials, chat history, learned personal memories, sticker collections or VM images are included. The official WeChat client and your own login approval remain necessary; DeepSeek itself does not connect to WeChat.

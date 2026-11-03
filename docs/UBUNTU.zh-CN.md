# Ubuntu 24.04 本地部署

这一版面向服务器机房里的 Ubuntu 24.04 LTS。Docker 内运行官方 Linux 微信、独立 X11 桌面、Baguet 控制器、原版 AstrBot/LivingMemory/Stealer；Ollama 为独立容器。无需 Mac、iPad、显示器或 macOS VM。普通微信账号由安装者自己选择，不要求小号。账号能否登录仍以微信实际验证为准。

**开发预览验收范围**：Ubuntu ARM64 镜像构建、官方微信扫码界面、设置面板、VNC 认证与工作进程恢复已实测。Linux 登录后的真实收发、识图、完整模型准备和长期记忆运行尚待端到端验收；amd64 也尚未实机验证。详情见 [VALIDATION.json](../VALIDATION.json)。

## 准备条件

- Ubuntu 24.04 LTS，amd64 或 arm64，能运行 Docker Engine + Compose v2。
- 建议 16 GB 以上内存、40 GB 以上空闲磁盘作为试用预算；32 GB 更适合同时做本地识图。这不是测得的最低要求。CPU 可以运行，但第一次识图会较慢。
- 可访问 Tencent 下载站、GitHub、Python 包仓库、Docker Hub、Ollama 模型仓库和 DeepSeek API 的网络。
- 自己的 DeepSeek API key，以及能扫码批准登录的微信手机。

Docker 未安装时按 [Docker 官方 Ubuntu 指南](https://docs.docker.com/engine/install/ubuntu/) 安装。脚本不会卸载机房现有 Docker、修改防火墙或替换别的容器。需要系统管理员安装 Docker 时，让管理员先完成这一步。

## 开始

解压完整包后，在包根目录运行：

```bash
bash Start.sh
```

第一次构建会下载官方微信和 Python 依赖，可能较久。成功后打开：

- 设置面板：<http://127.0.0.1:8766>
- 微信桌面：<http://127.0.0.1:8766/desktop.html>

1. 设置面板填写 API key、被 @ 时使用的名字和性格补充，点「保存」。key 仅保存在自己的 Docker 数据卷，权限 0600；面板不会回显。
2. 点「首次准备」。它建立自己的 QQ 框架实例、启动模型转发、通过原版接口设置人设、下载 bge-m3 和 Qwen3.5:2b，并做一次不发送微信消息的 DeepSeek 检查。普通回复的模型由 DeepSeek 提供，本地 Qwen 只做图片理解。可从列表选择你的 API 账号实际可用的 DeepSeek 模型。
3. 打开微信桌面，扫码登录要使用的账号，进入目标群或私聊。使用**浅色主题、100% 缩放**。桌面会固定在 1280×900，控制器会保持微信全屏。
4. 回设置面板点「读取当前聊天」。核对聊天名和账号图标，输入当前账号显示名，选择群聊或私聊，勾选已核对，再点「绑定此聊天」。这一步会读界面，不发消息。
5. 准备状态就绪后点「开始」。初始画面是历史基线，只处理之后的新消息。请用另一个联系人发送新消息，实际检查有没有新的微信出站气泡，以及接收端是否真的收到。

默认群聊被 @ 或被直接叫到时回应。「适度接话」允许选择性参与，不要求每句都答。文字通常一短句；保留原版 QQ 记忆、每五轮的反思，以及群内代写/角色覆盖限制。私聊也只开放当前明确选择的会话，不授予对方管理权限。

## 从 iPad 或另一台电脑管理服务器

网页默认只绑定服务器的本机地址。通过 SSH 转发使用，不需要把微信桌面公开上网：

```bash
ssh -L 8766:127.0.0.1:8766 -L 6080:127.0.0.1:6080 user@server
```

保持这次 SSH 连接，在访问端浏览器打开相同的 localhost 地址。iPad 需使用支持本地端口转发的 SSH 客户端，或由学校提供既有远程桌面。关闭浏览器、iPad、SSH 不会停止服务器上的 Docker 服务。

## 换聊天或账号

先点「暂停」，再在微信桌面打开另一个会话，重新读取、核对和绑定。每次只自动处理一个明确选定的聊天。换账号也需重新核对；本地消息去重和原版 QQ 长期记忆使用独立账号作用域。原有账号的记忆不会因为另一个账号用了相同群名而被带入。群名/布局/微信进程变化使绑定失效时，要重新读取和核对。不会自动跳到名字相近的群。

不把同一个账号在两套 Baguet 中同时启用；迁移时先暂停旧安装，再启用新安装。

## 停止、恢复和日志

```bash
docker compose ps
docker compose logs --tail 100 baguette
docker compose stop             # 停止，保留数据
docker compose up -d            # 再启动
```

设置面板的「暂停」会持久保存；进程监督不会自行撤销。监督器检测本项目的失联或超时工作进程，并只重启自己的工作进程。Docker 的 unless-stopped 策略负责容器退出后的重启。登录失效、绑定变化和不确定发送仍会阻止自动续聊。

一次发送只点一次。未观察到确切的新出站气泡会暂停。面板会显示该次原文；请在微信实际核对后再标记「已看到」。没有证据就保留阻断，不反复点击发送。这个检查不能证明收件方收到。

本机卷分别保存 Baguet 配置/记忆、微信自身账号数据、Ollama 模型。`docker compose stop` 不删除它们。不要在没有备份时使用 `docker compose down -v`。备份这些卷包含私人账号资料，应由部署者自己在服务器上保护；不要上传 GitHub 或公开分享。

## 当前边界

- Linux 控制器接入了现有 WeChat-AI 的截图、RapidOCR、YOLO 与布局识别；不启动其数据库/进程内存读取服务。
- 读取范围是当前会话的可见区域。群聊高速滚屏、OCR 失败、未加载图片、动图全部帧、语音/视频不保证覆盖。
- 可见图片进入原版 QQ Stealer + 本地 Qwen，再交给 DeepSeek。视觉解释可能出错。
- **Linux 收藏表情发送尚未校准**。本版明确拒绝该动作，让角色用简短文字回应；不会把选中一个 S 编号当成已经发出。原 macOS 的收藏发送实现和单独安装指南保留。
- 官方微信包由 Tencent 下载地址获取，安装时记录包版本；不同版本要重新做界面验收。模型和依赖也需要首次下载，ZIP 不是离线镜像。
- 不附带 Andy 的 key、聊天记录、人际记忆、微信收藏或 VM。每个人建立自己的数据。

## 来源

[AstrBot](https://github.com/AstrBotDevs/AstrBot)、[LivingMemory](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory)、[Stealer](https://github.com/nagatoquin33/astrbot_plugin_stealer)、[大肥鱼](https://github.com/whyever77/dafeiyu-astrbot) 是原有 QQ 组件；[WeChat-AI](https://github.com/ChisBread/wechat-ai) 提供 Linux 视觉组件，其代码源自 [omni-bot-sdk-oss](https://github.com/weixin-omni/omni-bot-sdk-oss)。固定版本见 UPSTREAMS.lock.json。桌面使用 [noVNC](https://github.com/novnc/noVNC)，本地模型服务使用 [Ollama 官方 Docker 镜像](https://docs.ollama.com/docker)。各自许可证保留。

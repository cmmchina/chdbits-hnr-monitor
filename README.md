# CHDBits H&R Monitor
本项目由Codex 自动化编写完成。

一个 Docker 友好的 H&R 进度监控器。它会定期读取 PT 站 H&R 页面，记录每个种子的进度字段。如果某个种子的进度字段在指定时间内没有变化，例如 24 小时，就通过控制台、邮件、Webhook、Hermes Agent、微信或 QQ 发送提醒。

项目默认不保存任何个人信息到仓库。Docker/NAS 推荐用环境变量配置；本机调试也可以使用 `config.toml`。

## 功能

- 监控 `hnr.php?id=用户ID` 页面
- 自动解析 HTML 表格中的种子、进度字段、状态和详情链接
- 使用 SQLite 保存历史状态
- 支持停滞阈值和重复提醒间隔
- 提醒中包含每条异常记录的 `标题` 和当前 `完成时间`
- 支持控制台、SMTP 邮件、通用 Webhook、Hermes Agent、企业微信群机器人微信提醒、OneBot v11 QQ 提醒
- 支持 Docker / Docker Compose
- 支持本地 HTML 样例解析，方便在不暴露 Cookie 的情况下校准页面结构

## 快速开始：Docker/NAS

NAS 上推荐用 Docker 环境变量，不需要单独挂载 `config.toml`。

```bash
cp .env.example .env
mkdir -p data
```

编辑 `.env`：

- `HNR_USER_ID` 改成你的用户 ID
- `CHDBITS_COOKIE` 填你的站点 Cookie
- 需要邮件提醒时，把 `HNR_EMAIL_ENABLED` 改成 `true`，并填写 SMTP 配置
- 需要 Hermes Agent 提醒时，把 `HNR_HERMES_ENABLED` 改成 `true`，并填写 Hermes 接收 URL
- 需要微信提醒时，把 `HNR_WECHAT_ENABLED` 改成 `true`，并填写企业微信群机器人 Webhook
- 需要 QQ 提醒时，把 `HNR_QQ_ENABLED` 改成 `true`，并填写 OneBot HTTP API 地址

导入镜像包后启动：

```bash
docker compose -f docker-compose.nas.yml up -d
```

查看日志：

```bash
docker logs -f chdbits-hnr-monitor
```

如果是在开发机上从源码构建，可以使用：

```bash
cp config.example.toml config.toml
docker compose -f docker-compose.example.yml up -d --build
```

## 常用环境变量

Docker/NAS 可以只靠环境变量运行，常用项如下：

- `HNR_BASE_URL`: 站点基础地址，默认 `https://ptchdbits.co`
- `HNR_PATH`: H&R 页面路径，默认 `/hnr.php`
- `HNR_USER_ID`: 你的用户 ID，必填
- `CHDBITS_COOKIE`: 站点 Cookie，必填
- `HNR_CHECK_INTERVAL_MINUTES`: 检查间隔分钟数，默认 `30`
- `HNR_STALLED_AFTER_HOURS`: 完成时间不变化多久后提醒，默认 `24`
- `HNR_NOTIFY_REPEAT_HOURS`: 同一记录重复提醒间隔，默认 `12`
- `HNR_TIMEZONE`: 显示和提醒使用的时区，默认 `Asia/Shanghai`
- `TZ`: 容器系统时区，建议和 `HNR_TIMEZONE` 一致
- `HNR_STATE_PATH`: SQLite 状态数据库路径，Docker 默认 `/data/hnr-monitor.sqlite3`
- `HNR_CONSOLE_ENABLED`: 是否在容器日志里输出提醒，默认 `true`
- `HNR_EMAIL_ENABLED`: 是否启用邮件提醒，`true` 或 `false`
- `HNR_SMTP_HOST`: SMTP 服务器
- `HNR_SMTP_PORT`: SMTP 端口，默认 `465`
- `HNR_SMTP_USE_SSL`: SMTP 是否使用 SSL，465 端口通常为 `true`
- `HNR_SMTP_STARTTLS`: SMTP 是否使用 STARTTLS，587 端口通常为 `true`
- `HNR_SMTP_USERNAME`: SMTP 用户名
- `HNR_SMTP_PASSWORD`: SMTP 密码或授权码
- `HNR_EMAIL_FROM`: 发件人
- `HNR_EMAIL_TO`: 收件人，多个邮箱用英文逗号分隔
- `HNR_WEBHOOK_ENABLED`: 是否启用 Webhook
- `HNR_WEBHOOK_URL`: Webhook 地址
- `HNR_HERMES_ENABLED`: 是否启用 Hermes Agent 提醒
- `HNR_HERMES_URL`: Hermes Agent 接收异常消息的 HTTP URL
- `HNR_HERMES_TOKEN`: Hermes Agent 鉴权 token，不需要鉴权时留空
- `HNR_HERMES_TOKEN_HEADER`: token 使用的请求头名，默认 `Authorization`
- `HNR_HERMES_TOKEN_PREFIX`: token 前缀，默认 `Bearer`；留空表示原样发送 token
- `HNR_HERMES_AGENT_NAME`: 发送给 Hermes 的来源名称
- `HNR_WECHAT_ENABLED`: 是否启用微信提醒，当前支持企业微信群机器人
- `HNR_WECHAT_PROVIDER`: 微信提醒提供方，当前固定为 `wecom_robot`
- `HNR_WECHAT_WEBHOOK_URL`: 企业微信群机器人 Webhook 地址
- `HNR_WECHAT_MSGTYPE`: 企业微信消息类型，`text` 或 `markdown`，默认 `text`
- `HNR_WECHAT_MENTION_MOBILES`: 可选，需要 @ 的手机号，多个用英文逗号分隔
- `HNR_WECHAT_MENTION_USER_IDS`: 可选，需要 @ 的企业微信用户 ID，多个用英文逗号分隔，仅 `text` 使用
- `HNR_WECHAT_AT_ALL`: 可选，是否 @所有人，`true` 或 `false`
- `HNR_QQ_ENABLED`: 是否启用 QQ 提醒，当前支持 OneBot v11 HTTP API
- `HNR_QQ_PROVIDER`: QQ 提醒提供方，当前固定为 `onebot_v11`
- `HNR_QQ_ONEBOT_URL`: OneBot HTTP API 基础地址，例如 `http://127.0.0.1:3000`
- `HNR_QQ_ONEBOT_TOKEN`: OneBot `access_token`，未设置鉴权时留空
- `HNR_QQ_MESSAGE_TYPE`: QQ 消息类型，`private` 发私聊，`group` 发群消息
- `HNR_QQ_USER_ID`: 私聊接收 QQ 号，`HNR_QQ_MESSAGE_TYPE=private` 时必填
- `HNR_QQ_GROUP_ID`: 接收 QQ 群号，`HNR_QQ_MESSAGE_TYPE=group` 时必填
- `HNR_QQ_AUTO_ESCAPE`: 是否把消息作为纯文本发送，默认 `true`

高级解析配置仍然可以放在 `config.toml` 里；如果不挂载配置文件，程序会使用内置默认解析规则，默认监控 `完成时间` 列。

镜像内已经预置了上述环境变量名称。导入镜像后在 NAS 界面新建容器时，通常能在环境变量列表里看到这些 `HNR_...` 项；只需要改值即可。Docker 镜像标准本身没有“环境变量说明文字”字段，所以说明同时写在镜像 `LABEL`、`.env.example` 和本文档里。

## Hermes Agent 对接

Hermes Agent 没有在本项目里内置固定协议假设；这里按 HTTP 接收器方式发送。你需要在 Hermes Agent 侧准备一个可接收 POST JSON 的 URL，然后把 URL 和可选鉴权 token 填到 Docker 环境变量里。

最小配置：

```env
HNR_HERMES_ENABLED=true
HNR_HERMES_URL=http://你的Hermes地址:端口/你的接收路径
```

如果 Hermes 端需要 token：

```env
HNR_HERMES_TOKEN=你的token
HNR_HERMES_TOKEN_HEADER=Authorization
HNR_HERMES_TOKEN_PREFIX=Bearer
```

发送给 Hermes 的 JSON 会同时包含人类可读文本和结构化异常数据，主要字段如下：

```json
{
  "source": "chdbits-hnr-monitor",
  "agent": "CHDBits H&R Monitor",
  "type": "hnr_stalled",
  "severity": "warning",
  "title": "H&R 监控提醒：1 个种子完成时间未变化",
  "message": "...完整提醒文本...",
  "alerts": [
    {
      "title": "种子标题",
      "completion_time": "12:34:56",
      "stalled_hours": 24.0,
      "detail_url": "https://..."
    }
  ]
}
```

保存后重建或重启容器，再测试通知：

```bash
docker exec -it chdbits-hnr-monitor hnr-monitor test-notify
```

如果 Hermes 接收器返回 HTTP 2xx，就会认为发送成功；如果返回 JSON 中包含 `{"ok": false}`、`{"success": false}` 或 `{"status": "error"}`，程序会记录为发送失败。

## 微信提醒对接

当前内置的是企业微信群机器人方式。它是官方支持的 Webhook 推送，适合把提醒发到一个只有你自己的企业微信群，或者发到家庭/运维提醒群。个人微信本身没有稳定公开的官方机器人接口，不建议用扫码挂机或非官方逆向方案。

对接步骤：

1. 在企业微信里创建或进入一个群聊。
2. 在群设置里添加“群机器人”，创建机器人后复制 Webhook 地址。官方说明见 [企业微信群机器人文档](https://developer.work.weixin.qq.com/document/path/91770)。
3. 在 NAS / Docker 环境变量里设置：

```env
HNR_WECHAT_ENABLED=true
HNR_WECHAT_PROVIDER=wecom_robot
HNR_WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的机器人key
HNR_WECHAT_MSGTYPE=text
```

可选 @ 自己：

```env
HNR_WECHAT_MENTION_MOBILES=你的手机号
```

保存后重建或重启容器，再测试通知：

```bash
docker exec -it chdbits-hnr-monitor hnr-monitor test-notify
```

如果你在微信里收到了“测试 H&R 种子”的提醒，就说明微信通道已经接通。真实异常提醒会和邮件一样，包含每条异常记录的 `标题`、当前 `完成时间`、未变化时长和链接。

## QQ 提醒对接

当前内置的是 OneBot v11 HTTP API。程序不会登录 QQ，也不会保存 QQ 密码；你需要另外运行一个兼容 OneBot v11 的 QQ 机器人实现，让本程序调用它的 HTTP API 发送消息。OneBot v11 的 HTTP 通信和 `send_private_msg`、`send_group_msg` 接口可参考 [OneBot v11 HTTP 通信文档](https://283375.github.io/onebot_v11_vitepress/communication/http.html) 和 [OneBot v11 API 文档](https://283375.github.io/onebot_v11_vitepress/api/public.html)。

常见思路是在 NAS 上运行一个 OneBot 实现，并开放 HTTP 地址，例如：

```env
HNR_QQ_ENABLED=true
HNR_QQ_PROVIDER=onebot_v11
HNR_QQ_ONEBOT_URL=http://onebot:3000
HNR_QQ_ONEBOT_TOKEN=
HNR_QQ_MESSAGE_TYPE=private
HNR_QQ_USER_ID=你的QQ号
```

如果要发到 QQ 群：

```env
HNR_QQ_MESSAGE_TYPE=group
HNR_QQ_GROUP_ID=你的QQ群号
```

保存后重建或重启容器，再测试通知：

```bash
docker exec -it chdbits-hnr-monitor hnr-monitor test-notify
```

如果 OneBot 端启用了 `access_token`，把同一个 token 填到 `HNR_QQ_ONEBOT_TOKEN`。如果 H&R 监控容器和 OneBot 容器在同一个 Docker Compose 网络里，`HNR_QQ_ONEBOT_URL` 可以写成 `http://onebot容器名:端口`；如果 OneBot 跑在宿主机或另一台 NAS 上，就填对应内网 IP 和端口。

## 本机测试

本机可以直接用源码运行。默认配置里的 `state_path` 是 Docker 路径 `/data/hnr-monitor.sqlite3`，本机测试时建议改成：

```toml
[monitor]
state_path = "./data/hnr-monitor.sqlite3"
```

解析公开示例：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml parse-fixture fixtures/sample_hnr.html
```

单次检查：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml once
```

常驻运行：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml run
```

测试通知：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml test-notify
```

模拟 2 条记录的 `完成时间` 停滞，用来测试真实报警内容：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml simulate-alert
```

`simulate-alert` 不访问网站，也不修改数据库，只用现有状态库里的记录生成一条模拟提醒。想测试完整“状态停滞 -> 抓取网页 -> 触发提醒”的流程，再使用：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml simulate-stall
PYTHONPATH=src python3 -m hnr_monitor --config config.toml once
```

`simulate-stall` 只修改本地 SQLite 状态库，不会改网站数据。默认模拟 2 条记录；如需模拟全部记录，可以加 `--all`。

## 校准真实 H&R 页面

因为 H&R 页面是登录后页面，建议先在浏览器中打开 H&R 页面，然后另存为 HTML，放到 `fixtures/private/hnr.html`。这个目录已经被 `.gitignore` 忽略。

查看页面表格摘要：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml parse-fixture fixtures/private/hnr.html --summary
```

解析记录：

```bash
PYTHONPATH=src python3 -m hnr_monitor --config config.toml parse-fixture fixtures/private/hnr.html
```

如果解析不到记录，优先调整 `config.toml` 里的这些字段：

- `parser.progress_columns`
- `parser.name_columns`
- `parser.status_columns`
- `parser.progress_column_index`
- `parser.name_column_index`
- `parser.status_column_index`

列索引从 `0` 开始。能用列名自动识别时，建议保持索引为 `-1`。

CHDBits 的 H&R 表格通常包含这些列：

- `标题`
- `H&R百分比`
- `剩余时间`
- `H&R周期`
- `做种时间`
- `下载时间`
- `上传`
- `下载`
- `分享率`
- `完成时间`

如果你的目标是监控 H&R 已完成时间，请优先监控 `完成时间`。默认配置已经把它放在第一优先级；只有页面表头变化或无法找到该列时，才会退到后面的候选字段。

## 配置说明

关键配置在 `config.example.toml`。

```toml
[monitor]
check_interval_minutes = 30
stalled_after_hours = 24
notify_repeat_hours = 12
timezone = "Asia/Shanghai"
```

含义：

- 每 30 分钟检查一次
- 进度字段连续 24 小时不变就提醒
- 同一种子提醒后，至少 12 小时后才会重复提醒
- 提醒时间按上海时区显示

## 隐私与开源

不要提交这些内容：

- `config.toml`
- `.env`
- SQLite 数据库
- 真实 H&R 页面 HTML
- Cookie、邮箱密码、手机号、Webhook URL

仓库默认已经忽略这些文件。

# CHDBits H&R Monitor
本项目由Codex 自动化编写完成。

一个 Docker 友好的 H&R 进度监控器。它会定期读取 PT 站 H&R 页面，记录每个种子的进度字段。如果某个种子的进度字段在指定时间内没有变化，例如 24 小时，就通过控制台、邮件或 Webhook 发送提醒。

项目默认不保存任何个人信息到仓库。Docker/NAS 推荐用环境变量配置；本机调试也可以使用 `config.toml`。

## 功能

- 监控 `hnr.php?id=用户ID` 页面
- 自动解析 HTML 表格中的种子、进度字段、状态和详情链接
- 使用 SQLite 保存历史状态
- 支持停滞阈值和重复提醒间隔
- 提醒中包含每条异常记录的 `标题` 和当前 `完成时间`
- 支持控制台、SMTP 邮件、通用 Webhook
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

高级解析配置仍然可以放在 `config.toml` 里；如果不挂载配置文件，程序会使用内置默认解析规则，默认监控 `完成时间` 列。

镜像内已经预置了上述环境变量名称。导入镜像后在 NAS 界面新建容器时，通常能在环境变量列表里看到这些 `HNR_...` 项；只需要改值即可。Docker 镜像标准本身没有“环境变量说明文字”字段，所以说明同时写在镜像 `LABEL`、`.env.example` 和本文档里。

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

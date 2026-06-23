ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HNR_BASE_URL=https://ptchdbits.co \
    HNR_PATH=/hnr.php \
    HNR_USER_ID=1 \
    CHDBITS_COOKIE= \
    HNR_CHECK_INTERVAL_MINUTES=30 \
    HNR_STALLED_AFTER_HOURS=24 \
    HNR_NOTIFY_REPEAT_HOURS=12 \
    HNR_TIMEZONE=Asia/Shanghai \
    TZ=Asia/Shanghai \
    HNR_STATE_PATH=/data/hnr-monitor.sqlite3 \
    HNR_CONSOLE_ENABLED=true \
    HNR_EMAIL_ENABLED=false \
    HNR_SMTP_HOST=smtp.example.com \
    HNR_SMTP_PORT=465 \
    HNR_SMTP_USE_SSL=true \
    HNR_SMTP_STARTTLS=false \
    HNR_SMTP_USERNAME= \
    HNR_SMTP_PASSWORD= \
    HNR_EMAIL_FROM= \
    HNR_EMAIL_TO= \
    HNR_WEBHOOK_ENABLED=false \
    HNR_WEBHOOK_URL= \
    HNR_HERMES_ENABLED=false \
    HNR_HERMES_URL= \
    HNR_HERMES_TOKEN= \
    HNR_HERMES_TOKEN_HEADER=Authorization \
    HNR_HERMES_TOKEN_PREFIX=Bearer \
    HNR_HERMES_HMAC_SECRET= \
    HNR_HERMES_SIGNATURE_HEADER=X-Hub-Signature-256 \
    HNR_HERMES_AGENT_NAME="CHDBits H&R Monitor" \
    HNR_WECHAT_ENABLED=false \
    HNR_WECHAT_PROVIDER=wecom_robot \
    HNR_WECHAT_WEBHOOK_URL= \
    HNR_WECHAT_MSGTYPE=text \
    HNR_WECHAT_MENTION_MOBILES= \
    HNR_WECHAT_MENTION_USER_IDS= \
    HNR_WECHAT_AT_ALL=false \
    HNR_QQ_ENABLED=false \
    HNR_QQ_PROVIDER=onebot_v11 \
    HNR_QQ_ONEBOT_URL= \
    HNR_QQ_ONEBOT_TOKEN= \
    HNR_QQ_MESSAGE_TYPE=private \
    HNR_QQ_USER_ID= \
    HNR_QQ_GROUP_ID= \
    HNR_QQ_AUTO_ESCAPE=true

LABEL org.opencontainers.image.title="CHDBits H&R Monitor" \
      org.opencontainers.image.description="监控 CHDBits H&R 页面的完成时间列，停滞后通过控制台、邮件、Webhook、Hermes Agent、微信或 QQ 提醒。" \
      hnr.env.HNR_BASE_URL="站点基础地址。默认 https://ptchdbits.co，一般不需要修改。" \
      hnr.env.HNR_PATH="H&R 页面路径。默认 /hnr.php，一般不需要修改。" \
      hnr.env.HNR_USER_ID="必填。PT 站用户 ID，例如 1。" \
      hnr.env.CHDBITS_COOKIE="必填。浏览器里的 CHDBits Cookie。" \
      hnr.env.HNR_CHECK_INTERVAL_MINUTES="检查周期，单位分钟。默认 30；例如 10 表示每 10 分钟检查一次。" \
      hnr.env.HNR_STALLED_AFTER_HOURS="完成时间连续多少小时不变化后提醒。默认 24。" \
      hnr.env.HNR_NOTIFY_REPEAT_HOURS="同一条异常重复提醒间隔，单位小时。默认 12。" \
      hnr.env.HNR_TIMEZONE="显示和提醒使用的时区。默认 Asia/Shanghai。" \
      hnr.env.TZ="容器系统时区。建议与 HNR_TIMEZONE 保持一致。" \
      hnr.env.HNR_STATE_PATH="SQLite 状态数据库路径。Docker 默认 /data/hnr-monitor.sqlite3。" \
      hnr.env.HNR_CONSOLE_ENABLED="是否在容器日志中输出提醒。true 或 false，默认 true。" \
      hnr.env.HNR_EMAIL_ENABLED="是否启用邮件提醒。true 或 false。" \
      hnr.env.HNR_SMTP_HOST="SMTP 服务器地址。" \
      hnr.env.HNR_SMTP_PORT="SMTP 端口。SSL 通常为 465，STARTTLS 通常为 587。" \
      hnr.env.HNR_SMTP_USE_SSL="SMTP 是否使用 SSL。465 端口通常为 true。" \
      hnr.env.HNR_SMTP_STARTTLS="SMTP 是否使用 STARTTLS。587 端口通常为 true；与 SSL 二选一。" \
      hnr.env.HNR_SMTP_USERNAME="SMTP 用户名，通常是邮箱地址。" \
      hnr.env.HNR_SMTP_PASSWORD="SMTP 密码或邮箱授权码。" \
      hnr.env.HNR_EMAIL_FROM="发件人邮箱。" \
      hnr.env.HNR_EMAIL_TO="收件人邮箱，多个用英文逗号分隔。" \
      hnr.env.HNR_WEBHOOK_ENABLED="是否启用 Webhook 提醒。true 或 false。" \
      hnr.env.HNR_WEBHOOK_URL="Webhook 地址。" \
      hnr.env.HNR_HERMES_ENABLED="是否启用 Hermes Agent 提醒。true 或 false。" \
      hnr.env.HNR_HERMES_URL="Hermes Agent 接收异常消息的 HTTP URL。" \
      hnr.env.HNR_HERMES_TOKEN="Hermes Agent 鉴权 token；不需要鉴权时留空。" \
      hnr.env.HNR_HERMES_TOKEN_HEADER="Hermes token 使用的请求头名。默认 Authorization。" \
      hnr.env.HNR_HERMES_TOKEN_PREFIX="Hermes token 前缀。默认 Bearer；留空表示原样发送 token。" \
      hnr.env.HNR_HERMES_HMAC_SECRET="Hermes Webhook HMAC Secret。设置后会发送 X-Hub-Signature-256: sha256=... 签名。" \
      hnr.env.HNR_HERMES_SIGNATURE_HEADER="Hermes HMAC 签名请求头名。默认 X-Hub-Signature-256。" \
      hnr.env.HNR_HERMES_AGENT_NAME="发送给 Hermes 的来源名称。默认 CHDBits H&R Monitor。" \
      hnr.env.HNR_WECHAT_ENABLED="是否启用微信提醒。true 或 false；当前支持企业微信群机器人。" \
      hnr.env.HNR_WECHAT_PROVIDER="微信提醒提供方。当前固定为 wecom_robot，表示企业微信群机器人。" \
      hnr.env.HNR_WECHAT_WEBHOOK_URL="企业微信群机器人 Webhook 地址，形如 https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." \
      hnr.env.HNR_WECHAT_MSGTYPE="企业微信消息类型。text 或 markdown，默认 text。" \
      hnr.env.HNR_WECHAT_MENTION_MOBILES="需要 @ 的手机号，多个用英文逗号分隔。" \
      hnr.env.HNR_WECHAT_MENTION_USER_IDS="需要 @ 的企业微信用户 ID，多个用英文逗号分隔；仅 text 类型使用。" \
      hnr.env.HNR_WECHAT_AT_ALL="是否 @所有人。true 或 false。" \
      hnr.env.HNR_QQ_ENABLED="是否启用 QQ 提醒。true 或 false；当前支持 OneBot v11 HTTP API。" \
      hnr.env.HNR_QQ_PROVIDER="QQ 提醒提供方。当前固定为 onebot_v11。" \
      hnr.env.HNR_QQ_ONEBOT_URL="OneBot HTTP API 基础地址，例如 http://127.0.0.1:3000。" \
      hnr.env.HNR_QQ_ONEBOT_TOKEN="OneBot access_token；如果你的 OneBot 未设置 token 可留空。" \
      hnr.env.HNR_QQ_MESSAGE_TYPE="QQ 消息类型。private 发私聊，group 发群消息。" \
      hnr.env.HNR_QQ_USER_ID="接收私聊消息的 QQ 号；HNR_QQ_MESSAGE_TYPE=private 时必填。" \
      hnr.env.HNR_QQ_GROUP_ID="接收群消息的 QQ 群号；HNR_QQ_MESSAGE_TYPE=group 时必填。" \
      hnr.env.HNR_QQ_AUTO_ESCAPE="是否把消息作为纯文本发送。true 或 false，默认 true。"

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

CMD ["hnr-monitor", "run"]

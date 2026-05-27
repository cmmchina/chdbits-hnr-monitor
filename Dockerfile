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
    HNR_WEBHOOK_URL=

LABEL org.opencontainers.image.title="CHDBits H&R Monitor" \
      org.opencontainers.image.description="监控 CHDBits H&R 页面的完成时间列，停滞后通过控制台、邮件或 Webhook 提醒。" \
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
      hnr.env.HNR_WEBHOOK_URL="Webhook 地址。"

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

CMD ["hnr-monitor", "run"]

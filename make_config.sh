# Экспортирую переменные окружения
source .env

cat >config.py <<EOF
# Конфигурация Telegram-бота

# Токен бота (получить у @BotFather в Telegram)
BOT_TOKEN = "$BOT_TOKEN"

# ID чата, куда отправлять уведомления (можно узнать через @userinfobot)
# Если оставить None, бот будет отправлять в тот чат, где была использована команда
CHAT_ID = "$CHAT_ID"

# Время отправки уведомлений (часы:минуты) по UTC
NOTIFICATION_TIME = "06:00"
EOF

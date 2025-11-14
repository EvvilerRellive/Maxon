
# Maxon — Развертывание бота для Max Messenger

## Обзор
Maxon — это бот-напоминалка для мессенджера Max. Пользователь отправляет время (`HH:MM`, `HH:MM DD.MM` или `HH:MM DD.MM.YYYY`), затем текст напоминания отдельным сообщением. Бот сохраняет напоминания и отправляет их в нужное время.

## Возможности
- ✅ Гибкий разбор времени (только время, с датой, с годом)
- ✅ Постоянное хранение напоминаний (JSON-файл)
- ✅ Список напоминаний (`/note`)
- ✅ Удаление напоминаний (`/notedel N`)
- ✅ Лимит напоминаний на пользователя (по умолчанию 10)
- ✅ WebHook-режим для продакшена
- ✅ Long-polling для разработки

## Быстрый старт (разработка)

### Требования
- Python 3.10+
- Токен API Max Messenger

### Установка и запуск (long-polling)

1. Создать и активировать виртуальное окружение:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Установить зависимости:
```powershell
pip install -r requirements.txt
```

3. Установить токен бота (на сессию):
```powershell
$env:MAX_ACCESS_TOKEN = "ваш_реальный_токен"
```

4. Запустить бота (long-polling):
```powershell
python bot.py
```

В логах будут отображаться полученные сообщения и запланированные напоминания. Для остановки — Ctrl+C.

## Продакшен-развертывание (WebHook)

### Почему WebHook?
- Надежнее: Max сам отправляет обновления на ваш endpoint
- Масштабируемо: можно обслуживать много пользователей
- Продакшен-стандарт: правильная HTTP-семантика

### Требования для WebHook
- Публичный HTTPS-домен/URL
- Порт: 80, 8080, 443, 8443 или 16384–32383
- SSL/TLS-сертификат (можно Let's Encrypt)
- Сервер работает 24/7

### Варианты развертывания

#### Вариант A: Docker + облако (проще всего)

1. **Собрать Docker-образ:**
```powershell
# В корне проекта
docker build -t maxon-bot .
```

2. **Протестировать локально:**
```powershell
$env:MAX_ACCESS_TOKEN = "ваш_токен"
$env:WEBHOOK_SECRET = "секрет-12345"
docker run -e MAX_ACCESS_TOKEN=$env:MAX_ACCESS_TOKEN `
          -e WEBHOOK_SECRET=$env:WEBHOOK_SECRET `
          -p 8000:8000 `
          maxon-bot
```
В браузере http://localhost:8000 должен появиться Uvicorn.

3. **Задеплоить на Render** (есть бесплатный тариф):
   - Зарегистрироваться на https://render.com
   - Подключить GitHub-репозиторий
   - Создать "New Web Service"
   - Build command: `pip install -r requirements.txt`
   - Start command: `python webhook.py`
   - Установить переменные окружения:
     - `MAX_ACCESS_TOKEN`: ваш токен
     - `WEBHOOK_SECRET`: ваш секрет
   - Deploy

   После деплоя URL будет вида `https://maxon-bot-xxxxx.onrender.com`

4. **Подписаться на WebHook в Max API:**
```powershell
$env:MAX_ACCESS_TOKEN = "ваш_токен"
$env:WEBHOOK_URL = "https://maxon-bot-xxxxx.onrender.com/updates"
$env:WEBHOOK_SECRET = "секрет-12345"

# Запустить PowerShell-скрипт подписки
.\examples\subscribe.ps1
# (Перед запуском отредактируйте $webhookUrl и $secret)
```

Или через curl (bash):
```bash
curl -X POST "https://platform-api.max.ru/subscriptions?access_token=ВАШ_ТОКЕН" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your.domain/updates",
    "update_types": ["message_created"],
    "secret": "секрет-12345"
  }'
```

#### Вариант B: VPS + systemd + nginx (полный контроль)

1. **SSH на VPS** (рекомендуется Ubuntu 20.04 LTS):
```bash
ssh user@your.vps.ip
```

2. **Установка:**
```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/maxon.git
cd maxon

# Создать venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Создать .env
cat > .env << EOF
MAX_ACCESS_TOKEN=ваш_токен
WEBHOOK_SECRET=секрет-12345
EOF
chmod 600 .env
```

3. **Создать systemd-сервис:**
Создать `/etc/systemd/system/maxon-bot.service`:
```ini
[Unit]
Description=Maxon Bot WebHook Service
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/maxon
EnvironmentFile=/home/botuser/maxon/.env
ExecStart=/home/botuser/maxon/venv/bin/python webhook.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Включить и запустить:
```bash
sudo systemctl enable maxon-bot
sudo systemctl start maxon-bot
sudo systemctl status maxon-bot
```

4. **Настроить nginx reverse proxy:**
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Создать конфиг nginx
sudo tee /etc/nginx/sites-available/maxon > /dev/null << 'EOF'
server {
    listen 80;
    server_name your.domain;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/maxon /etc/nginx/sites-enabled/

# Получить SSL-сертификат
sudo certbot --nginx -d your.domain

# Перезапустить nginx
sudo systemctl restart nginx
```

5. **Подписаться на WebHook:**
```bash
curl -X POST "https://platform-api.max.ru/subscriptions?access_token=ВАШ_ТОКЕН" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your.domain/updates",
    "update_types": ["message_created"],
    "secret": "секрет-12345"
  }'
```

6. **Смотреть логи:**
```bash
sudo journalctl -u maxon-bot -f
```

### Конфигурация

Редактировать `config.json`:
```json
{
  "access_token": "",  // Оставьте пустым, используйте переменную окружения
  "timezone": "UTC+3",  // Часовой пояс пользователя (поддержка UTC±N)
  "max_reminders_per_user": 10,  // Лимит
  "storage_file": "data/reminders.json",
  "webhook_secret": "",  // Опционально, или через переменную окружения
  "poll_interval_seconds": 5,  // Интервал проверки планировщика
  "updates_timeout_seconds": 30  // Таймаут long-poll
}
```

## Использование

### Основные команды

1. **Создать напоминание:**
   - Отправьте: `10:30` → бот спросит текст
   - Отправьте: `Купить молоко` → напоминание на сегодня 10:30 (или завтра, если время прошло)

2. **С датой:**
   - `10:30 17.11` → напоминание 17 ноября в 10:30
   - `10:30 17.11.2026` → напоминание 17 ноября 2026 в 10:30

3. **Список напоминаний:**
   - `/note` → бот покажет все активные напоминания с номерами

4. **Удалить напоминание:**
   - `/notedel 1` → удалить напоминание №1

## API эндпоинты (WebHook)

- `POST /updates` — получать обновления Max API (WebHook)
- `GET /health` — проверка здоровья
- `GET /` — информация о сервисе

## Устранение неполадок

### Бот не получает сообщения
- Проверьте подписку WebHook: `GET /subscriptions?access_token=ТОКЕН`
- Если WebHook активен, long-polling не будет получать обновления (они взаимоисключающие)
- Если подписки нет, long-polling включен по умолчанию

### Как отписаться от WebHook:
```powershell
# PowerShell
$token = $env:MAX_ACCESS_TOKEN
$url = [System.Uri]::EscapeDataString("https://your.domain/updates")
Invoke-RestMethod -Uri "https://platform-api.max.ru/subscriptions?access_token=$token&url=$url" -Method Delete
```

Или используйте `examples/unsubscribe.ps1`.

### Логи
- Разработка: вывод в консоль (INFO)
- Продакшен (systemd): `sudo journalctl -u maxon-bot -f`
- Docker: `docker logs container_id -f`

## Структура файлов
```
maxon/
├── bot.py                 # Основная логика бота (разбор сообщений, напоминания)
├── webhook.py             # FastAPI WebHook сервер
├── storage.py             # Постоянное JSON-хранилище
├── config.json            # Конфиг (часовой пояс, лимиты и т.д.)
├── requirements.txt       # Python зависимости
├── Dockerfile             # Docker-образ
└── examples/
    ├── subscribe.ps1      # Подписка на WebHook (PowerShell)
    ├── unsubscribe.ps1    # Отписка от WebHook (PowerShell)
    └── subscribe.sh       # Подписка на WebHook (bash)
```

## Лицензия
MIT (2025)

## Ссылки
- [Документация Max Bot API](https://dev.max.ru/docs-api/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Render Deployment](https://render.com/docs)

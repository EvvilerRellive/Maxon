
# Maxon — Бот-напоминалка для Max Messenger

Простой и надежный бот для платформы [Max Messenger](https://max.ru/). Пользователи отправляют время в гибких форматах, затем текст напоминания, и бот отправляет уведомления в запланированное время.

**Возможности:**
- ✅ Гибкий разбор времени: `HH:MM`, `HH:MM DD-MM`, `HH:MM DD-MM-YYYY`
- ✅ Постоянное хранение напоминаний в JSON (сохраняются при перезапусках)
- ✅ Команды: `/note` (показать напоминания), `/notedel N` (удалить напоминание N), `/cash` (показать финансовую историю)
- ✅ Отслеживание финансовых транзакций: `+300 Категория` (доход) или `-200 Категория` (расход) — одной строкой или в два шага
- ✅ Поддержка часового пояса для каждого пользователя (формат UTC+N через `/settz`, `/gettz`)
- ✅ Настраиваемый лимит напоминаний на пользователя (по умолчанию: 10)
- ✅ WebHook режим для продакшена (обновления в реальном времени)
- ✅ Long-polling режим для разработки
- ✅ Контейнеризация с Docker (готов к облачному развертыванию)
- ✅ Потокобезопасное хранилище с автоматическим сохранением

---

## Быстрый старт (локальный Docker)

### Требования
- Установлены Docker и Docker Compose
- Токен Max Bot API (получить на [platform.max.ru/dev/bots](https://platform.max.ru/dev/bots))

### Настройка

1. **Склонировать репозиторий:**
```bash
git clone https://github.com/yourusername/Maxon.git
cd Maxon
```

2. **Создать файл `.env` с вашими учетными данными:**
```bash
cp .env.example .env
# Отредактируйте .env и добавьте ваш MAX_ACCESS_TOKEN (получить из Max Developer Portal)
```

3. **Запустить бота с помощью Docker Compose:**
```bash
docker-compose up -d
```

4. **Проверить работу:**
```bash
# Просмотреть логи
docker-compose logs -f maxon-bot

# Проверить endpoint здоровья
curl http://localhost:8000/health
# Ожидаемый ответ: {"status": "ok"}
```

5. **Остановить бота:**
```bash
docker-compose down
```

---

### Запуск с `docker run`

Если вы хотите запускать контейнер без `docker-compose`, используйте прямую сборку и `docker run`.

1) Собрать образ локально:
```powershell
docker build -t maxon-bot .
```

2) Запустить контейнер (пример, пробрасываем порт 8000 и передаём токен):
```powershell

```

3) Проверить логи контейнера:
```powershell
docker logs -f maxon-bot
```

4) Остановить и удалить контейнер:
```powershell
docker stop maxon-bot
docker rm maxon-bot
```

Примечания:
- `MAX_ACCESS_TOKEN` обязателен — приложение завершит работу без токена.
- Переключение режимов: установите переменную `BOT_MODE` в `bot`, `webhook` или `both` для управления поведением контейнера.
- Для продакшен-развертывания используйте безопасное хранение секретов (Docker secrets, переменные окружения в CI/CD, Vault и т.п.).

### Вложенный образ в репозитории

Для удобства в корне репозитория добавлен tar-архив Docker-образа `maxon-bot.tar`. Его можно загрузить и использовать локально без сборки:

```powershell
# Загрузить образ из архива
docker load -i maxon-bot.tar

# Запустить как обычно
docker run -d --name maxon-bot -e MAX_ACCESS_TOKEN="ВАШ_ТОКЕН" -p 8000:8000 maxon-bot
```

Примечание: хранение бинарных tar-файлов образов в git увеличивает размер репозитория. Рассмотрите публикацию образа в Docker Hub или другом реестре для удобства и экономии места.

## Тестирование в Max Messenger

1. **Получить токен бота:**
   - Перейти на [platform.max.ru/dev/bots](https://platform.max.ru/dev/bots)
   - Создать нового бота или использовать существующего
   - Скопировать API токен в файл `.env`

2. **Добавить бота в чат:**
   - Открыть Max Messenger
   - Создать новый чат или использовать существующий
   - Добавить вашего бота как участника

3. **Протестировать команды напоминаний:**
   - Отправить время: `15:30` (сегодня в 15:30)
   - В следующем сообщении отправить текст напоминания: `Купить продукты`
   - Бот подтверждает: "Напоминание установлено"
   - В 15:30 бот отправит: "Напоминание: Купить продукты"

4. **Другие команды:**
  - `/note` — показать все ваши активные напоминания (время показывается в вашем настроенном часовом поясе)
  - `/notedel 1` — удалить напоминание #1
  - `/cash` — показать вашу недавнюю историю финансовых транзакций

**Финансовые транзакции (новая функция):**
  - Отправьте `+300` для записи дохода или `-200` для записи расхода
  - Бот спросит категорию (например, "Подработка", "Продукты")
  - Отправьте категорию в следующем сообщении
  - Бот запишет: сумму, категорию, дату
  - Просмотр истории через `/cash`

Дополнительные вспомогательные команды:
  - `/time` или `/now` — показать текущее время (в вашем часовом поясе)
  - `/help` — показать справку по боту (команды и форматы)
  - `/settz <UTC+N>` — установить ваш личный часовой пояс (примеры: `/settz UTC+3`, `/settz UTC-5`, `/settz UTC+5:30`)
  - `/gettz` — показать ваш настроенный часовой пояс в формате UTC+N
  - `/main` — управление флагами функций: `/main notifications on|off`, `/main transactions on|off`

---

## Структура проекта

```
.
├── bot.py              # Основная логика бота (разбор сообщений, напоминания, планировщик)
├── storage.py          # Постоянное JSON хранилище (потокобезопасное)
├── webhook.py          # FastAPI WebHook сервер для обновлений Max
├── config.json         # Конфигурация (часовой пояс, лимиты, пути)
├── Dockerfile          # Определение Docker образа
├── docker-compose.yml  # Локальная настройка Docker Compose
├── requirements.txt    # Python зависимости
├── .env.example        # Шаблон окружения (скопировать в .env)
├── data/               # Постоянное хранилище (создается при запуске)
├── examples/           # Вспомогательные скрипты
│   ├── subscribe.ps1   # PowerShell: подписка на WebHook
│   ├── subscribe.sh    # Bash: подписка на WebHook
│   └── unsubscribe.ps1 # PowerShell: отписка от WebHook
└── CI-CD.md           # Руководство по продакшен развертыванию (GitHub Actions + Docker Hub + VPS)
```

---

## Как это работает

### Режим Long-Polling (разработка)
Бот запускается локально, непрерывно опрашивает Max API на новые сообщения:
```powershell
# Терминал 1: Установить токен
$env:MAX_ACCESS_TOKEN = "your_token_here"

# Терминал 2: Запустить бота
python bot.py
```

### Режим WebHook (продакшен)
Бот работает на VPS с публичным HTTPS endpoint. Max отправляет обновления напрямую на ваш сервер:
- Быстрее: нет задержки опроса
- Масштабируемо: обработка большего количества пользователей
- Готово к продакшену: правильная HTTP семантика

**Для продакшен развертывания** см. [CI-CD.md](CI-CD.md) для полной настройки GitHub Actions + Docker Hub + VPS.

---

## Конфигурация

Отредактируйте `config.json` для настройки:

```json
{
  "access_token": "",
  "timezone": "UTC+3",
  "storage_file": "data/reminders.json",
  "max_reminders_per_user": 10,
  "updates_timeout_seconds": 30,
  "poll_interval_seconds": 5,
  "webhook_secret": ""
}
```

**Переменные окружения переопределяют config.json:**
- `MAX_ACCESS_TOKEN` — токен API бота (рекомендуется: использовать переменную окружения, не config.json)
- `WEBHOOK_SECRET` — опциональный секрет для валидации WebHook

---

## Разработка

### Запуск без Docker (локальный Python)

```powershell
# Создать виртуальное окружение
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Установить зависимости
pip install -r requirements.txt

# Запустить бота (long-polling)
$env:MAX_ACCESS_TOKEN = "your_token_here"
python bot.py

# Или запустить WebHook сервер
python webhook.py
```

### Примечания о формате файлов

**Разбор времени (в сообщениях пользователей):**
- `15:30` — сегодня в 15:30 (или завтра если время прошло)
- `15:30 25-12` — 25 декабря в 15:30 (этот год или следующий если прошло)
- `15:30 25-12-2025` — 25 декабря 2025 в 15:30 (точно)
- Поддерживаются форматы как с дефисом (`25-12`), так и с точкой (`25.12`) для совместимости

**Хранилище (`data/reminders.json`):**
```json
{
  "reminders": [
    {
      "id": "uuid-string",
      "user_id": 12345,
      "time": 1734076200000,
      "text": "Купить продукты",
      "sent": false
    }
  ],
  "pending": {
    "12345": 1734072600.123
  },
  "user_timezones": {
    "12345": "UTC+3"
  },
  "transactions": [
    {
      "id": "uuid-string",
      "user_id": 12345,
      "amount": 300,
      "category": "Подработка",
      "timestamp": 1734076200000
    },
    {
      "id": "uuid-string",
      "user_id": 12345,
      "amount": -200,
      "category": "Продукты",
      "timestamp": 1734072600000
    }
  ],
  "pending_transactions": {
    "12345": 150
  }
}
```

Примечания:
- `user_timezones` хранит строки часового пояса для каждого пользователя в формате UTC+N (например, `UTC+3`, `UTC-5`, `UTC+5:30`). Все времена напоминаний и даты транзакций отображаются пользователям в их настроенном часовом поясе.
- Времена напоминаний хранятся как epoch миллисекунды в UTC, чтобы они срабатывали правильно независимо от часового пояса сервера.
- `transactions` хранит все записи о доходах/расходах с timestamp, категорией и знаковой суммой (положительная = доход, отрицательная = расход).
- `pending_transactions` временно хранит сумму, пока пользователь не предоставит категорию.

---

## API Endpoints (WebHook режим)

| Endpoint | Метод | Назначение |
|----------|--------|---------|
| `/updates` | POST | Получить обновления Max Bot API (требуется валидный заголовок `X-Max-Bot-Api-Secret`) |
| `/health` | GET | Проверка здоровья (возвращает `{"status": "ok"}`) |
| `/` | GET | Корневой endpoint с базовой информацией |

---

## Устранение неполадок

### Бот не получает сообщения
- **Проверьте токен:** Убедитесь что `MAX_ACCESS_TOKEN` установлен правильно
- **Проверьте логи Docker:** `docker-compose logs maxon-bot`
- **Убедитесь что бот добавлен в чат:** Удостоверьтесь что бот является участником чата
- **Проверьте статус Max API:** Посетите [platform.max.ru](https://platform.max.ru)

### Напоминания не отправляются
- **Проверьте часовой пояс:** Конфиг содержит `"timezone": "UTC+3"` — настройте при необходимости
- **Проверьте что контейнер работает:** `docker-compose ps`
- **Проверьте директорию data:** `data/reminders.json` должен существовать с записями напоминаний
- **Проверьте логи:** `docker-compose logs -f maxon-bot | grep "Напоминание"`

### Порт уже используется
- Измените порт Docker в `docker-compose.yml`: `"127.0.0.1:9000:8000"` (привязывает хост порт 9000 к контейнеру 8000)
- Или остановите другой сервис: `docker-compose down` или `lsof -i :8000`

---

## Развертывание

### Локальное тестирование
Следуйте "Быстрому старту" выше — запускает бота в Docker на localhost:8000

### Продакшен (VPS/облако)
См. [CI-CD.md](CI-CD.md) для:
- Рабочего процесса GitHub Actions (автоматическая сборка Docker образа)
- Реестра Docker Hub (хранение образов)
- Развертывания VPS (docker-compose + nginx + certbot HTTPS)
- Подписки WebHook на Max API

---

## Лицензия

MIT © 2025 Участники Maxon

---

## Поддержка

- **Max Messenger:** https://max.ru
- **Max Developer Portal:** https://platform.max.ru/dev
- **Max Bot API Документация:** https://platform-api.max.ru/doc

2. **Create `.env` file with your credentials:**
```bash
cp .env.example .env
# Edit .env and add your MAX_ACCESS_TOKEN (get from Max Developer Portal)
```

3. **Start the bot with Docker Compose:**
```bash
docker-compose up -d
```

4. **Verify it's running:**
```bash
# Check logs
docker-compose logs -f maxon-bot

# Test health endpoint
curl http://localhost:8000/health
# Expected response: {"status": "ok"}
```

5. **Stop the bot:**
```bash
docker-compose down
```

---

## Testing on Max Messenger

1. **Get your bot token:**
   - Go to [platform.max.ru/dev/bots](https://platform.max.ru/dev/bots)
   - Create a new bot or use existing one
   - Copy the API token to `.env` file

2. **Add bot to a chat:**
   - Open Max Messenger
   - Create a new chat or use existing one
   - Add your bot as a participant

3. **Test reminder commands:**
   - Send a time: `15:30` (today at 3:30 PM)
   - In next message, send reminder text: `Buy groceries`
   - Bot confirms: "Напоминание установлено" (Reminder set)
   - At 15:30, bot sends: "Напоминание: Buy groceries"

4. **Other commands:**
  - `/note` — show all your active reminders (times shown in your configured timezone)
  - `/notedel 1` — delete reminder #1
  - `/cash` — show your recent financial transaction history

**Financial Transactions (New Feature):**
  - Send `+300` to record income, or `-200` to record expense
  - Bot asks for category (e.g., "Подработка", "Продукты")
  - Send the category in your next message
  - Bot records: amount, category, date
  - View history with `/cash`

Additional utility commands:
  - `/time` or `/now` — show current time (in your timezone)
  - `/help` — show bot help (commands and formats)
  - `/settz <UTC+N>` — set your personal timezone (examples: `/settz UTC+3`, `/settz UTC-5`, `/settz UTC+5:30`)
  - `/gettz` — show your configured timezone in UTC+N format
  - `/main` — manage feature flags: `/main notifications on|off`, `/main transactions on|off`

---

## Project Structure

```
.
├── bot.py              # Core bot logic (message parsing, reminders, scheduler)
├── storage.py          # Persistent JSON storage (thread-safe)
├── webhook.py          # FastAPI WebHook server for Max updates
├── config.json         # Configuration (timezone, limits, paths)
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Local Docker Compose setup
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template (copy to .env)
├── data/               # Persistent storage (created at runtime)
├── examples/           # Helper scripts
│   ├── subscribe.ps1   # PowerShell: subscribe to WebHook
│   ├── subscribe.sh    # Bash: subscribe to WebHook
│   └── unsubscribe.ps1 # PowerShell: unsubscribe from WebHook
└── CI-CD.md           # Production deployment guide (GitHub Actions + Docker Hub + VPS)
```

---

## How It Works

### Long-Polling Mode (Development)
Bot runs locally, continuously polls Max API for new messages:
```powershell
# Terminal 1: Set token
$env:MAX_ACCESS_TOKEN = "your_token_here"

# Terminal 2: Run bot
python bot.py
```

### WebHook Mode (Production)
Bot runs on VPS with public HTTPS endpoint. Max sends updates directly to your server:
- Faster: no polling delay
- Scalable: handle more users
- Production-ready: proper HTTP semantics

**For production deployment**, see [CI-CD.md](CI-CD.md) for full GitHub Actions + Docker Hub + VPS setup.

---

## Configuration

Edit `config.json` to customize:

```json
{
  "access_token": "",
  "timezone": "UTC+3",
  "storage_file": "data/reminders.json",
  "max_reminders_per_user": 10,
  "updates_timeout_seconds": 30,
  "poll_interval_seconds": 5,
  "webhook_secret": ""
}
```

**Environment variables override config.json:**
- `MAX_ACCESS_TOKEN` — bot API token (recommended: use env var, not config.json)
- `WEBHOOK_SECRET` — optional secret for WebHook validation

---

## Development

### Run without Docker (local Python)

```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run bot (long-polling)
$env:MAX_ACCESS_TOKEN = "your_token_here"
python bot.py

# Or run WebHook server
python webhook.py
```

### File Format Notes

**Time Parsing (in user messages):**
- `15:30` — today at 3:30 PM (or tomorrow if time has passed)
- `15:30 25-12` — Dec 25 at 3:30 PM (this year or next if passed)
- `15:30 25-12-2025` — Dec 25, 2025 at 3:30 PM (exact)
- Both dash (`25-12`) and dot (`25.12`) formats are supported for compatibility

**Storage (`data/reminders.json`):**
```json
{
  "reminders": [
    {
      "id": "uuid-string",
      "user_id": 12345,
      "time": 1734076200000,
      "text": "Buy groceries",
      "sent": false
    }
  ],
  "pending": {
    "12345": 1734072600.123
  },
  "user_timezones": {
    "12345": "UTC+3"
  },
  "transactions": [
    {
      "id": "uuid-string",
      "user_id": 12345,
      "amount": 300,
      "category": "Подработка",
      "timestamp": 1734076200000
    },
    {
      "id": "uuid-string",
      "user_id": 12345,
      "amount": -200,
      "category": "Продукты",
      "timestamp": 1734072600000
    }
  ],
  "pending_transactions": {
    "12345": 150
  }
}
```

Notes:
- `user_timezones` stores per-user timezone strings in UTC+N format (e.g. `UTC+3`, `UTC-5`, `UTC+5:30`). All reminder times and transaction dates are displayed to users in their configured timezone.
- Reminder times are stored as epoch milliseconds in UTC so they fire correctly regardless of server timezone.
- `transactions` stores all income/expense records with timestamp, category, and signed amount (positive = income, negative = expense).
- `pending_transactions` temporarily stores amount while waiting for user to provide category.

---

## API Endpoints (WebHook Mode)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/updates` | POST | Receive Max Bot API updates (requires valid `X-Max-Bot-Api-Secret` header) |
| `/health` | GET | Health check (returns `{"status": "ok"}`) |
| `/` | GET | Root endpoint with basic info |

---

## Troubleshooting

### Bot not receiving messages
- **Check token:** Ensure `MAX_ACCESS_TOKEN` is set correctly
- **Check Docker logs:** `docker-compose logs maxon-bot`
- **Verify bot added to chat:** Make sure bot is participant in the chat
- **Check Max API status:** Visit [platform.max.ru](https://platform.max.ru)

### Reminders not sending
- **Check timezone:** Config has `"timezone": "UTC+3"` — adjust if needed
- **Verify container is running:** `docker-compose ps`
- **Check data directory:** `data/reminders.json` should exist with reminder entries
- **Check logs:** `docker-compose logs -f maxon-bot | grep "Напоминание"`

### Port already in use
- Change Docker port in `docker-compose.yml`: `"127.0.0.1:9000:8000"` (maps host 9000 to container 8000)
- Or stop other service: `docker-compose down` or `lsof -i :8000`

---

## Deployment

### Local Testing
Follow "Quick Start" above — runs bot in Docker on localhost:8000

### Production (VPS/Cloud)
See [CI-CD.md](CI-CD.md) for:
- GitHub Actions workflow (automated Docker image build)
- Docker Hub registry (store images)
- VPS deployment (docker-compose + nginx + certbot HTTPS)
- WebHook subscription to Max API

---

## License

MIT © 2025 Maxon Contributors

---

## Support

- **Max Messenger:** https://max.ru
- **Max Developer Portal:** https://platform.max.ru/dev
- **Max Bot API Docs:** https://platform-api.max.ru/doc
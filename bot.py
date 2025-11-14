import json
import time
import threading
from datetime import datetime, timedelta
import requests
from dateutil import tz
import os
import logging
import re

from storage import Storage

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

API_BASE = 'https://platform-api.max.ru'
# Предпочтительно использовать переменную окружения для токена (не храните токены в репозитории)
TOKEN = os.environ.get('MAX_ACCESS_TOKEN') or cfg.get('access_token')
if not TOKEN:
    print('Ошибка: токен доступа не предоставлен. Установите переменную окружения MAX_ACCESS_TOKEN или добавьте access_token в config.json')
    raise SystemExit(1)

# базовое логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def utc_offset_to_tz(utc_str: str):
    """Преобразует строку UTC+N или UTC-N в объект tzoffset."""
    try:
        utc_str = utc_str.strip().upper()
        if utc_str.startswith('UTC'):
            offset_part = utc_str[3:]
            if offset_part.startswith('+'):
                offset_part = offset_part[1:]
            if ':' in offset_part:
                hours, minutes = offset_part.split(':')
                total_seconds = int(hours) * 3600 + int(minutes) * 60 * (1 if int(hours) >= 0 else -1)
            else:
                total_seconds = int(offset_part) * 3600
            return tz.tzoffset(None, total_seconds)
        return tz.gettz(utc_str)
    except Exception:
        return None


def tz_to_utc_offset(tz_str: str) -> str:
    """Преобразует строку временной зоны IANA или UTC+N в формат UTC+N."""
    try:
        if tz_str.upper().startswith('UTC'):
            return tz_str.upper()
        tz_obj = tz.gettz(tz_str)
        if not tz_obj:
            return tz_str
        now_utc = datetime.now(tz=tz.tzutc())
        now_local = now_utc.astimezone(tz_obj)
        offset = now_local.utcoffset().total_seconds() / 3600
        offset_int = int(offset)
        if offset == offset_int:
            return f"UTC+{offset_int}" if offset_int >= 0 else f"UTC{offset_int}"
        else:
            minutes = int((offset - offset_int) * 60)
            return f"UTC+{offset_int}:{minutes:02d}" if offset_int >= 0 else f"UTC{offset_int}:{minutes:02d}"
    except Exception:
        return tz_str


def send_message(chat_id=None, user_id=None, text='', attachments=None, fmt=None):
    url = API_BASE + '/messages'
    params = {}
    if chat_id:
        params['chat_id'] = chat_id
    if user_id:
        params['user_id'] = user_id
    body = {'text': text}
    if attachments is not None:
        body['attachments'] = attachments
    if fmt in ('markdown', 'html'):
        body['format'] = fmt
    try:
        headers = {'Authorization': TOKEN}
        resp = requests.post(url, params=params, json=body, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning('send_message failed %s %s', resp.status_code, resp.text)
        else:
            logger.info('send_message OK to user=%s chat=%s', user_id, chat_id)
        return resp
    except Exception as e:
        logger.exception('send_message exception')
        return None


def answer_callback(callback_id: str, message_body: dict = None, notification: str = None):
    """Отправить ответ на callback: опционально отредактировать сообщение и/или отправить одноразовое уведомление."""
    url = API_BASE + '/answers'
    params = {'callback_id': callback_id}
    body = {}
    if message_body is not None:
        body['message'] = message_body
    if notification is not None:
        body['notification'] = notification
    try:
        headers = {'Authorization': TOKEN}
        resp = requests.post(url, params=params, json=body, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning('answer_callback failed %s %s', resp.status_code, resp.text)
        else:
            logger.info('answer_callback OK for callback_id=%s', callback_id)
        return resp
    except Exception:
        logger.exception('answer_callback exception')
        return None


def build_main_keyboard(notifications_on: bool, transactions_on: bool):
    """Построить вложения с inline клавиатурой для переключателей /main."""
    notif_text = f"🔔 Уведомления: {'Вкл' if notifications_on else 'Выкл'}"
    trans_text = f"💸 Транзакции: {'Вкл' if transactions_on else 'Выкл'}"
    attachments = [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {"type": "callback", "text": notif_text, "payload": "toggle:notifications"}
                    ],
                    [
                        {"type": "callback", "text": trans_text, "payload": "toggle:transactions"}
                    ]
                ]
            }
        }
    ]
    return attachments


class Bot:
    def __init__(self, storage: Storage):
        self.storage = storage
        self.marker = None

    def long_poll(self):
        url = API_BASE + '/updates'
        while True:
            params = {'timeout': cfg.get('updates_timeout_seconds', 30)}
            if self.marker is not None:
                params['marker'] = self.marker
            try:
                logger.debug('Long polling %s', params)
                headers = {'Authorization': TOKEN}
                r = requests.get(url, params=params, headers=headers, timeout=cfg.get('updates_timeout_seconds', 35))
                if r.status_code == 200:
                    data = r.json()
                    updates = data.get('updates', [])
                    logger.info('Received %d updates (marker=%s)', len(updates), data.get('marker'))
                    if updates:
                        for u in updates:
                            try:
                                logger.debug('Update: %s', u)
                                self.handle_update(u)
                            except Exception:
                                logger.exception('Error handling update')
                        self.marker = data.get('marker', self.marker)
                else:
                    logger.warning('Long poll returned %s: %s', r.status_code, r.text[:200])
                    time.sleep(1)
            except Exception:
                logger.exception('Exception in long_poll')
                time.sleep(2)

    def handle_update(self, update):
        ut = update.get('update_type')
        logger.info('Handle update type=%s', ut)
        if ut == 'message_created':
            msg = update.get('message', {})
            body = msg.get('body', {})
            text = body.get('text') or ''
            chat = msg.get('recipient', {})
            chat_id = chat.get('chat_id')
            user = msg.get('sender', {})
            user_id = user.get('user_id')

            # обработка простых команд
            text_stripped = text.strip()
            if text_stripped.lower() == '/note':
                if not self.storage.get_feature('notifications'):
                    send_message(user_id=user_id, text='Функционал уведомлений отключен')
                    return
                items = self.storage.list_reminders(user_id)
                if not items:
                    send_message(user_id=user_id, text='Нет напоминаний')
                else:
                    lines = []
                    user_tz_str = self.storage.get_user_tz(user_id) or cfg.get('timezone', 'UTC+3')
                    user_tz = utc_offset_to_tz(user_tz_str) or tz.tzlocal()
                    for i, it in enumerate(items, 1):
                        ts = datetime.fromtimestamp(it['time'] / 1000, tz=tz.tzutc()).astimezone(user_tz)
                        time_str = ts.strftime('%H:%M')
                        lines.append(f"{i}. {time_str} — {it['text']}")
                    send_message(user_id=user_id, text='\n'.join(lines))
                return

            if text_stripped.lower().startswith('/notedel'):
                if not self.storage.get_feature('notifications'):
                    send_message(user_id=user_id, text='Функционал уведомлений отключен')
                    return
                parts = text_stripped.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    idx = int(parts[1]) - 1
                    ok = self.storage.delete_reminder_by_index(user_id, idx)
                    send_message(user_id=user_id, text='Удалено' if ok else 'Не найдено')
                else:
                    send_message(user_id=user_id, text='Использование: /notedel N')
                return

            # Показать текущее время в часовом поясе пользователя
            if text_stripped.lower() in ('/time', '/now'):
                now_utc = datetime.now(tz=tz.tzutc())
                user_tz_str = self.storage.get_user_tz(user_id) or cfg.get('timezone', 'UTC+3')
                user_tz = utc_offset_to_tz(user_tz_str)
                if not user_tz:
                    user_tz = tz.tzutc()
                now_local = now_utc.astimezone(user_tz)
                local_time = now_local.strftime('%H:%M')
                send_message(user_id=user_id, text=local_time)
                return

            # Команды для часового пояса: /settz <UTC+N> и /gettz
            if text_stripped.lower().startswith('/settz'):
                parts = text_stripped.split(maxsplit=1)
                if len(parts) < 2 or not parts[1]:
                    send_message(user_id=user_id, text='Использование: /settz UTC+3 или /settz UTC-5')
                    return
                tz_candidate = parts[1].strip()
                if not utc_offset_to_tz(tz_candidate):
                    send_message(user_id=user_id, text='Неверная временная зона. Примеры: UTC+3, UTC-5, UTC+5:30')
                    return
                self.storage.set_user_tz(user_id, tz_candidate)
                send_message(user_id=user_id, text=f'Временная зона установлена: {tz_candidate}')
                return

            if text_stripped.lower() == '/gettz':
                user_tz = self.storage.get_user_tz(user_id)
                if user_tz:
                    utc_offset = tz_to_utc_offset(user_tz)
                    send_message(user_id=user_id, text=f'Ваша временная зона: {utc_offset}')
                else:
                    global_tz = cfg.get("timezone", "UTC+3")
                    utc_offset = tz_to_utc_offset(global_tz) if not global_tz.startswith('UTC') else global_tz
                    send_message(user_id=user_id, text=f'Используется глобальная временная зона: {utc_offset}')
                return

            # Команда помощи: список доступных команд и форматов
            if text_stripped.lower() == '/help':
                help_text = (
                    "Доступные команды:\n"
                    "/help — показать это сообщение\n"
                    "/time или /now — показать текущее время\n"
                    "/note — показать ваши активные напоминания (только при notifications on)\n"
                    "/notedel N — удалить напоминание с номером N (только при notifications on)\n"
                    "/cash [day|week|month|year|dd-mm-yy|dd-mm-yy - dd-mm-yy] — показать историю транзакций (только при transactions on)\n"
                    "/settz <UTC+N> — установить временную зону (пример: /settz UTC+3)\n"
                    "/gettz — показать вашу временную зону\n"
                    "/main — управление функционалом (Уведомления, Транзакции)\n\n"
                    "Создание напоминаний (notifications on):\n"
                    "• 16:30 Покормить кота — одной строкой\n"
                    "• 16:30 — затем следующим сообщением текст\n"
                    "Форматы времени: hh:mm | hh:mm dd-mm | hh:mm dd-mm-yyyy\n\n"
                    "Финансовые транзакции (transactions on):\n"
                    "• +300 Продукты — одной строкой\n"
                    "• +300 — затем следующим сообщением категория\n"
                    "Отрицательные значения для расходов: -200 Такси"
                )
                send_message(user_id=user_id, text=help_text)
                return

            # Команда /main для переключения функций: /main notifications on/off, /main transactions on/off
            if text_stripped.lower().startswith('/main'):
                parts = text_stripped.split()
                if len(parts) == 1:
                    # показать текущие флаги с inline клавиатурой
                    notif = self.storage.get_feature('notifications')
                    trans = self.storage.get_feature('transactions')
                    text_main = (
                        "Главное меню\n\n"
                        f"Уведомления: {'on' if notif else 'off'}\n"
                        f"Транзакции: {'on' if trans else 'off'}\n\n"
                        "Нажмите кнопку, чтобы переключить"
                    )
                    send_message(user_id=user_id, text=text_main, attachments=build_main_keyboard(notif, trans))
                    return
                if len(parts) >= 3:
                    feature = parts[1].lower()
                    val = parts[2].lower()
                    if feature not in ('notifications', 'transactions'):
                        send_message(user_id=user_id, text='Неверный флаг. Допустимо: notifications, transactions')
                        return
                    if val in ('on', '1', 'true'):
                        self.storage.set_feature(feature, True)
                        send_message(user_id=user_id, text=f'{feature} включен')
                        return
                    if val in ('off', '0', 'false'):
                        self.storage.set_feature(feature, False)
                        send_message(user_id=user_id, text=f'{feature} отключен')
                        return
                    send_message(user_id=user_id, text='Использование: /main <feature> on|off')
                    return

            # Транзакции: /cash [day|week|month|year|dd-mm-yy|dd-mm-yy-dd-mm-yy]
            if text_stripped.lower().startswith('/cash'):
                if not self.storage.get_feature('transactions'):
                    send_message(user_id=user_id, text='Функционал транзакций отключен')
                    return
                # определить диапазон
                parts = text_stripped.split(maxsplit=1)
                user_tz_str = self.storage.get_user_tz(user_id) or cfg.get('timezone', 'UTC+3')
                user_tz = utc_offset_to_tz(user_tz_str) or tz.tzlocal()
                now_local = datetime.now(tz=user_tz)

                def start_of_day(dt):
                    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

                def end_of_day(dt):
                    return dt.replace(hour=23, minute=59, second=59, microsecond=999000)

                start_local = None
                end_local = None
                if len(parts) == 1:
                    # по умолчанию: последние 10 записей
                    tx = self.storage.get_transactions(user_id, limit=10)
                else:
                    arg = parts[1].strip().lower()
                    if arg in ('day', 'сегодня'):
                        start_local = start_of_day(now_local)
                        end_local = now_local
                    elif arg == 'week':
                        dow = now_local.weekday()  # Monday=0
                        start_local = start_of_day(now_local - timedelta(days=dow))
                        end_local = now_local
                    elif arg == 'month':
                        start_local = start_of_day(now_local.replace(day=1))
                        end_local = now_local
                    elif arg == 'year':
                        start_local = start_of_day(now_local.replace(month=1, day=1))
                        end_local = now_local
                    else:
                        # дата или диапазон дат
                        try:
                            # Принимаются форматы dd.mm.yy и dd-mm-yy, а также диапазоны с опциональными пробелами вокруг '-'
                            date_re = r"^(\d{1,2})([.-])(\d{1,2})\2(\d{2,4})$"
                            range_re = r"^(\d{1,2}([.-])\d{1,2}\2\d{2,4})\s*-\s*(\d{1,2}([.-])\d{1,2}\4\d{2,4})$"
                            m_range = re.match(range_re, arg)
                            if m_range:
                                left = m_range.group(1)
                                right = m_range.group(3)
                                m1 = re.match(date_re, left)
                                m2 = re.match(date_re, right)
                                d1, sep1, mo1, y1 = m1.group(1), m1.group(2), m1.group(3), m1.group(4)
                                d2, sep2, mo2, y2 = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
                                y1i = int(y1); y2i = int(y2)
                                y1i = 2000 + y1i if y1i < 100 else y1i
                                y2i = 2000 + y2i if y2i < 100 else y2i
                                start_local = datetime(y1i, int(mo1), int(d1), tzinfo=user_tz)
                                end_local = end_of_day(datetime(y2i, int(mo2), int(d2), tzinfo=user_tz))
                            else:
                                m = re.match(date_re, arg)
                                if not m:
                                    raise ValueError('bad date')
                                d, sep, mo, y = m.group(1), m.group(2), m.group(3), m.group(4)
                                yi = int(y)
                                yi = 2000 + yi if yi < 100 else yi
                                start_local = datetime(yi, int(mo), int(d), tzinfo=user_tz)
                                end_local = now_local
                        except Exception:
                            send_message(user_id=user_id, text='Неверный формат. Примеры: day | week | month | year | 01-10-25 | 01-10-25 - 14-10-25')
                            return

                    if start_local and end_local:
                        start_ms = int(start_local.astimezone(tz.tzutc()).timestamp() * 1000)
                        end_ms = int(end_local.astimezone(tz.tzutc()).timestamp() * 1000)
                        tx = sorted(self.storage.get_transactions_in_range(user_id, start_ms, end_ms), key=lambda x: x['timestamp'], reverse=True)
                    else:
                        tx = self.storage.get_transactions(user_id, limit=10)

                if not tx:
                    send_message(user_id=user_id, text='Нет транзакций')
                else:
                    lines = []
                    for t in tx:
                        ts = datetime.fromtimestamp(t['timestamp'] / 1000, tz=tz.tzutc()).astimezone(user_tz)
                        date_str = ts.strftime('%d.%m')
                        amount_str = f"+{t['amount']}" if t['amount'] > 0 else f"-{abs(t['amount'])}"
                        lines.append(f"{date_str} {amount_str} — {t['category']}")
                    send_message(user_id=user_id, text='\n'.join(lines))
                return

            # Резервные обработчики: транзакции и напоминания
            # 1) Транзакции: +300 [Категория] или -200 [Категория]
            trans_match_inline = re.match(r'^([+-])(\d+)(?:\s+(.+))?$', text_stripped)
            if trans_match_inline:
                if not self.storage.get_feature('transactions'):
                    send_message(user_id=user_id, text='Функционал транзакций отключен')
                    return
                sign = trans_match_inline.group(1)
                amount = int(trans_match_inline.group(2))
                if sign == '-':
                    amount = -amount
                category_inline = trans_match_inline.group(3)
                if category_inline:
                    timestamp_ms = int(datetime.now(tz=tz.tzutc()).timestamp() * 1000)
                    self.storage.add_transaction(user_id, amount, category_inline.strip(), timestamp_ms)
                    send_message(user_id=user_id, text=f'Транзакция записана: {sign}{abs(amount)} ({category_inline.strip()})')
                    return
                self.storage.set_pending_transaction_amount(user_id, amount)
                send_message(user_id=user_id, text='Укажите категорию (например, "Подработка" или "Продукты")')
                return

            # 2) Ожидание категории транзакции
            pending_trans_amount = self.storage.get_pending_transaction_amount(user_id)
            if pending_trans_amount is not None:
                if not self.storage.get_feature('transactions'):
                    self.storage.clear_pending_transaction(user_id)
                    send_message(user_id=user_id, text='Функционал транзакций отключен — транзакция отменена')
                    return
                timestamp_ms = int(datetime.now(tz=tz.tzutc()).timestamp() * 1000)
                self.storage.add_transaction(user_id, pending_trans_amount, text_stripped, timestamp_ms)
                self.storage.clear_pending_transaction(user_id)
                sign = '+' if pending_trans_amount > 0 else '-'
                send_message(user_id=user_id, text=f'Транзакция записана: {sign}{abs(pending_trans_amount)} ({text_stripped})')
                return

            # 3) Напоминания: разбор времени и опциональный встроенный текст
            user_tz_for_parse = self.storage.get_user_tz(user_id) or cfg.get('timezone', 'UTC+3')
            parsed = try_parse_time(text_stripped, user_tz_for_parse)
            if parsed:
                if not self.storage.get_feature('notifications'):
                    send_message(user_id=user_id, text='Функционал уведомлений отключен')
                    return
                self.storage.set_pending_text(user_id, parsed)
                send_message(user_id=user_id, text='Отправьте текст напоминания в следующем сообщении')
                return

            # 3a) Напоминание одной строкой: HH:MM <текст>
            m_time_text = re.match(r'^(\d{1,2}:\d{2})\s+(.+)$', text_stripped)
            if m_time_text:
                if not self.storage.get_feature('notifications'):
                    send_message(user_id=user_id, text='Функционал уведомлений отключен')
                    return
                hhmm = m_time_text.group(1)
                rem_text = m_time_text.group(2).strip()
                parsed_time_only = try_parse_time(hhmm, user_tz_for_parse)
                if parsed_time_only:
                    dt_ms = int(parsed_time_only.astimezone(tz.tzutc()).timestamp() * 1000)
                    success, msg = self.storage.add_reminder(user_id, dt_ms, rem_text)
                    send_message(user_id=user_id, text=msg)
                    return

            # 4) Ожидание напоминания: следующее сообщение — текст
            pending = self.storage.get_pending(user_id)
            if pending:
                if not self.storage.get_feature('notifications'):
                    self.storage.clear_pending(user_id)
                    send_message(user_id=user_id, text='Функционал уведомлений отключен — создание отменено')
                    return
                dt_ms = int(pending.timestamp() * 1000)
                success, msg = self.storage.add_reminder(user_id, dt_ms, text_stripped)
                self.storage.clear_pending(user_id)
                send_message(user_id=user_id, text=msg)
                return

        # Обработка callback'ов от inline клавиатуры
        if ut == 'message_callback':
            cb = update.get('callback', {})
            cb_id = cb.get('callback_id') or cb.get('id')
            payload = cb.get('payload') or cb.get('data') or ''
            # Переключить функции при нажатии кнопки
            if isinstance(payload, str) and payload.startswith('toggle:') and cb_id:
                feature = payload.split(':', 1)[1]
                if feature in ('notifications', 'transactions'):
                    current = self.storage.get_feature(feature)
                    self.storage.set_feature(feature, not current)
                    # Построить обновленное тело сообщения
                    notif = self.storage.get_feature('notifications')
                    trans = self.storage.get_feature('transactions')
                    text_main = (
                        "Главное меню\n\n"
                        f"Уведомления: {'on' if notif else 'off'}\n"
                        f"Транзакции: {'on' if trans else 'off'}\n\n"
                        "Нажмите кнопку, чтобы переключить"
                    )
                    message_body = {
                        'text': text_main,
                        'attachments': build_main_keyboard(notif, trans)
                    }
                    answer_callback(cb_id, message_body=message_body, notification=None)
                    return
            # Если payload неизвестен, просто подтвердить молча, чтобы убрать загрузчик
            if cb_id:
                answer_callback(cb_id, message_body=None, notification=None)
            return


def try_parse_time(text: str, tz_str='UTC+3'):
    # Принимает: HH:MM, HH:MM DD.MM, HH:MM DD.MM.YYYY
    parts = text.split()
    try:
        time_part = parts[0]
        dt = None
        # определить часовой пояс из tz_str (формат UTC+N). По умолчанию — локальный.
        user_tz = utc_offset_to_tz(tz_str) or tz.tzlocal()
        now = datetime.now(tz=user_tz)
        if len(parts) == 1:
            # только время
            hh, mm = map(int, time_part.split(':'))
            candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if candidate < now:
                candidate = candidate + timedelta(days=1)
            dt = candidate
        else:
            # есть дата (поддерживаются форматы DD.MM и DD-MM)
            date_part = parts[1]
            # нормализация: заменить '-' на '.' для унифицированного разбора
            date_part_normalized = date_part.replace('-', '.')
            if date_part_normalized.count('.') == 1:
                # DD.MM -> год = этот год или следующий, если прошло
                d, m = map(int, date_part_normalized.split('.'))
                hh, mm = map(int, time_part.split(':'))
                candidate = datetime(now.year, m, d, hh, mm, tzinfo=user_tz)
                if candidate < now:
                    candidate = candidate.replace(year=now.year + 1)
                dt = candidate
            elif date_part_normalized.count('.') == 2:
                d, m, y = map(int, date_part_normalized.split('.'))
                hh, mm = map(int, time_part.split(':'))
                candidate = datetime(y, m, d, hh, mm, tzinfo=user_tz)
                dt = candidate
        return dt
    except Exception:
        return None


def scheduler_thread(storage: Storage):
    while True:
        now_ms = int(datetime.now(tz=tz.tzlocal()).timestamp() * 1000)
        due = storage.get_due(now_ms)
        for rem in due:
            # Проверить глобальный флаг функции перед отправкой уведомлений
            if storage.get_feature('notifications'):
                send_message(user_id=rem['user_id'], text=f"Напоминание: {rem['text']}")
                storage.mark_sent(rem['id'])
        time.sleep(cfg.get('poll_interval_seconds', 5))


# Глобальный экземпляр бота (используется обработчиком webhook)
_bot_instance = None


def get_bot():
    """Получить или создать глобальный экземпляр бота."""
    global _bot_instance
    if _bot_instance is None:
        os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
        storage = Storage(cfg['storage_file'], cfg['max_reminders_per_user'])
        _bot_instance = Bot(storage)
    return _bot_instance


def main():
    bot = get_bot()
    storage = bot.storage

    th = threading.Thread(target=bot.long_poll, daemon=True)
    th.start()
    sch = threading.Thread(target=scheduler_thread, args=(storage,), daemon=True)
    sch.start()

    print('Bot started. Ctrl+C to stop.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping...')


if __name__ == '__main__':
    main()

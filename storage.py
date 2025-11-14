import json
import threading
import uuid
from typing import List, Optional
from dateutil import tz


class Storage:
    def __init__(self, path: str, max_per_user: int = 10):
        self.path = path
        self.max_per_user = max_per_user
        self.lock = threading.Lock()
        self._data = {'reminders': [], 'pending': {}, 'user_timezones': {}, 'transactions': [], 'pending_transactions': {}, 'features': {'notifications': True, 'transactions': True}}
        self._load()

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        except Exception:
            self._data = {'reminders': [], 'pending': {}, 'user_timezones': {}, 'transactions': [], 'pending_transactions': {}, 'features': {'notifications': True, 'transactions': True}}

    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def set_pending_text(self, user_id: int, dt):
        with self.lock:
            # Сохранить как UTC timestamp (dt ожидается timezone-aware)
            self._data['pending'][str(user_id)] = dt.astimezone(tz.tzutc()).timestamp()
            self._save()

    def get_pending(self, user_id: int):
        ts = self._data['pending'].get(str(user_id))
        if ts:
            from datetime import datetime
            # вернуть timezone-aware UTC datetime для ожидающего времени
            return datetime.fromtimestamp(ts, tz=tz.tzutc())
        return None

    def clear_pending(self, user_id: int):
        with self.lock:
            if str(user_id) in self._data['pending']:
                del self._data['pending'][str(user_id)]
                self._save()

    def set_user_tz(self, user_id: int, tz_str: str):
        """Установить строку часового пояса пользователя (IANA или UTC offset)."""
        with self.lock:
            self._data.setdefault('user_timezones', {})[str(user_id)] = tz_str
            self._save()

    def get_user_tz(self, user_id: int):
        """Получить строку часового пояса пользователя или None."""
        return self._data.get('user_timezones', {}).get(str(user_id))

    def clear_user_tz(self, user_id: int):
        with self.lock:
            if str(user_id) in self._data.get('user_timezones', {}):
                del self._data['user_timezones'][str(user_id)]
                self._save()

    def add_reminder(self, user_id: int, time_ms: int, text: str):
        with self.lock:
            user_rems = [r for r in self._data['reminders'] if r['user_id'] == user_id and not r.get('sent')]
            if len(user_rems) >= self.max_per_user:
                return False, f'Достигнут лимит напоминаний ({self.max_per_user})'
            rid = str(uuid.uuid4())
            rem = {'id': rid, 'user_id': user_id, 'time': time_ms, 'text': text, 'sent': False}
            self._data['reminders'].append(rem)
            self._save()
            return True, 'Напоминание установлено'

    def list_reminders(self, user_id: int):
        with self.lock:
            return [r for r in self._data['reminders'] if r['user_id'] == user_id and not r.get('sent')]

    def delete_reminder_by_index(self, user_id: int, idx: int):
        with self.lock:
            items = [r for r in self._data['reminders'] if r['user_id'] == user_id and not r.get('sent')]
            if 0 <= idx < len(items):
                rid = items[idx]['id']
                self._data['reminders'] = [r for r in self._data['reminders'] if r['id'] != rid]
                self._save()
                return True
            return False

    def get_due(self, now_ms: int):
        with self.lock:
            due = [r for r in self._data['reminders'] if not r.get('sent') and r['time'] <= now_ms]
            return due

    def mark_sent(self, rid: str):
        with self.lock:
            for r in self._data['reminders']:
                if r['id'] == rid:
                    r['sent'] = True
            self._save()

    def set_pending_transaction_amount(self, user_id: int, amount: int):
        """Сохранить сумму (+/-) и ожидать категорию."""
        with self.lock:
            self._data.setdefault('pending_transactions', {})[str(user_id)] = amount
            self._save()

    def get_pending_transaction_amount(self, user_id: int):
        """Получить ожидающую сумму транзакции или None."""
        return self._data.get('pending_transactions', {}).get(str(user_id))

    def clear_pending_transaction(self, user_id: int):
        with self.lock:
            if str(user_id) in self._data.get('pending_transactions', {}):
                del self._data['pending_transactions'][str(user_id)]
                self._save()

    def add_transaction(self, user_id: int, amount: int, category: str, timestamp_ms: int):
        """Добавить транзакцию в историю."""
        with self.lock:
            tid = str(uuid.uuid4())
            trans = {'id': tid, 'user_id': user_id, 'amount': amount, 'category': category, 'timestamp': timestamp_ms}
            self._data.setdefault('transactions', []).append(trans)
            self._save()
            return True

    def get_transactions(self, user_id: int, limit: int = 10):
        """Получить последние транзакции пользователя."""
        with self.lock:
            user_trans = [t for t in self._data.get('transactions', []) if t['user_id'] == user_id]
            return sorted(user_trans, key=lambda x: x['timestamp'], reverse=True)[:limit]

    def get_transactions_in_range(self, user_id: int, start_ts_ms: int, end_ts_ms: int):
        """Получить транзакции пользователя в диапазоне [start, end] включительно (временные метки в ms)."""
        with self.lock:
            user_trans = [t for t in self._data.get('transactions', []) if t['user_id'] == user_id]
            return [t for t in user_trans if start_ts_ms <= int(t['timestamp']) <= end_ts_ms]

    # Методы для флагов функций
    def set_feature(self, name: str, enabled: bool):
        """Установить флаг функции (глобально). Примеры имен: 'notifications', 'transactions'."""
        with self.lock:
            self._data.setdefault('features', {})[name] = bool(enabled)
            self._save()

    def get_feature(self, name: str) -> bool:
        """Получить значение флага функции; по умолчанию False, если отсутствует."""
        return bool(self._data.get('features', {}).get(name, False))

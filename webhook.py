"""
FastAPI WebHook-сервер для обновлений Max Bot API.
Принимает POST /updates от Max, проверяет секрет, обрабатывает через Bot.handle_update.
"""

import json
import logging
import os
import sys
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Header
import uvicorn

# Импорт логики бота
from bot import get_bot, cfg

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title='Max Bot WebHook')

# WebHook-секрет (опционально, но рекомендуется для безопасности)
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET') or cfg.get('webhook_secret', '')


@app.post('/updates')
async def webhook_updates(request: Request, x_max_bot_api_secret: Optional[str] = Header(None)):
    """
    Получить и обработать обновления Max Bot API через WebHook.
    
    POST body: Max Update JSON (такой же, как в GET /updates response.updates[i])
    Header: X-Max-Bot-Api-Secret (опционально, проверяется если WEBHOOK_SECRET установлен)
    
    Возвращает 200 при успехе, 400/401 при ошибке валидации.
    """
    try:
        # Проверить секрет, если настроен
        if WEBHOOK_SECRET:
            if not x_max_bot_api_secret or x_max_bot_api_secret != WEBHOOK_SECRET:
                logger.warning('Webhook secret validation failed')
                raise HTTPException(status_code=401, detail='Invalid secret')
        
        # Разобрать JSON тело
        body = await request.json()
        logger.info('Received webhook update: %s', body.get('update_type'))
        
        # Проверить минимальную структуру
        if 'update_type' not in body or 'timestamp' not in body:
            logger.warning('Invalid update structure: missing required fields')
            raise HTTPException(status_code=400, detail='Missing update_type or timestamp')
        
        # Обработать обновление через обработчик бота
        bot = get_bot()
        try:
            bot.handle_update(body)
        except Exception:
            logger.exception('Error handling update in bot')
            # Все равно вернуть 200 для подтверждения получения; Max повторит при non-200
            # (мы не хотим, чтобы Max продолжал попытки из-за внутренних ошибок)
        
        return {'success': True}
    
    except HTTPException:
        raise
    except Exception:
        logger.exception('Exception in webhook_updates')
        raise HTTPException(status_code=500, detail='Internal server error')


@app.get('/health')
async def health_check():
    """Эндпоинт проверки здоровья для мониторинга."""
    return {'status': 'ok'}


@app.get('/')
async def root():
    """Корневой эндпоинт с базовой информацией."""
    return {
        'name': 'Max Bot WebHook',
        'endpoints': ['/updates (POST)', '/health (GET)', '/ (GET)']
    }


if __name__ == '__main__':
    # Запустить: python webhook.py
    # Или: uvicorn webhook:app --host 0.0.0.0 --port 8000 --reload
    logger.info('Starting Max Bot WebHook server...')
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        log_level='info'
    )

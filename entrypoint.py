#!/usr/bin/env python3
"""
Скрипт точки входа, который запускает бота с long-polling и WebHook-сервер.
Позволяет гибкое развертывание: можно запустить только бота, только webhook или оба.
"""

import os
import threading
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def run_bot():
    """Запустить long-polling бота"""
    logger.info('Starting long-polling bot...')
    from bot import main
    main()

def run_webhook():
    """Запустить WebHook FastAPI сервер"""
    logger.info('Starting WebHook server...')
    import uvicorn
    from webhook import app
    
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        log_level='info'
    )

if __name__ == '__main__':
    # Получить режим из переменной окружения или командной строки
    # Допустимые режимы: 'bot', 'webhook', 'both' (по умолчанию: 'both')
    mode = os.environ.get('BOT_MODE', 'both').lower()
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    logger.info(f'Running in mode: {mode}')
    
    if mode == 'bot':
        # Запустить только long-polling бота
        run_bot()
    
    elif mode == 'webhook':
        # Запустить только WebHook-сервер
        run_webhook()
    
    elif mode == 'both':
        # Запустить оба: WebHook-сервер в главном потоке, бота в фоновом потоке
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logger.info('Bot thread started, running WebHook server on main thread...')
        run_webhook()
    
    else:
        logger.error(f'Unknown mode: {mode}. Use: bot, webhook, or both')
        sys.exit(1)

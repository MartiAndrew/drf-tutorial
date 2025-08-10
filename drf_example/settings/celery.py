import sys

from django.conf import settings

# Детекция запущено ли сейчас тестирование
TESTING = 'test' in sys.argv
TESTING = TESTING or 'test_coverage' in sys.argv or 'pytest' in sys.modules

CELERY = {  # в дев настройках немного переопределяем, не забудьте про это
    'broker_url': 'redis://localhost:6379/0',  # URL брокера сообщений
    'task_always_eager': TESTING,  # Синхронное выполнение задач при тестировании
    'timezone': settings.TIME_ZONE,  # Временная зона для планировщика
    'result_backend': 'django-db',
    'result_extended': True,
    'task_track_started': True,  # Статус "started" для задач
}

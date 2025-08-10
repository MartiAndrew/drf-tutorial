import os
import random
from time import sleep

from billiard.exceptions import SoftTimeLimitExceeded

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drf_example.settings')

from celery import Celery, shared_task

from drf_example.settings.celery import CELERY

# Set the default Django settings module for the 'celery' program.

app = Celery('proj')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object(CELERY)

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Настройка очередей с разными приоритетами
app.conf.task_queues = {
    'high': {'exchange': 'high', 'routing_key': 'high'},
    'default': {'exchange': 'default', 'routing_key': 'default'},
}

# Установка маршрутизации задач по очередям
app.conf.task_routes = {
    'drf_example.celery.update_example_name': {'queue': 'high'},
    'drf_example.celery.very_long_task': {'queue': 'default'},
    'drf_example.celery.debug_task': {'queue': 'default'},
}

@app.task(
    bind=True,
    max_retries=5,  # Максимальное количество повторных попыток
    acks_late=True,               # Подтверждать задачу только после успешного выполнения
    reject_on_worker_lost=True,   # Возвращать задачу в очередь при сбое воркера
)
def debug_task(self):
    print(f'Request: {self.request!r}')
    self.update_state(
        meta={
            'progress': '50%',
            'finished': 4,
            'total': 8,
        }
    )
    try:
        if random.choice([True, False]):
            raise ValueError('Error')
    except ValueError as e:
        raise self.retry(exc=e)  # Повторная попытка через 10 секунд
    return 1

@app.task(
    bind=True,
)
def very_long_task(self):
    try:
        sleep(60)
    except SoftTimeLimitExceeded:
        return 0
    return 1

@app.task
def update_example_name(example_id, new_name):
    from drf_example.apps.example.models import ExampleModel
    example = ExampleModel.objects.get(id=example_id)
    example.name = new_name
    example.save()
    return example.name

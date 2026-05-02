from celery import Celery

from app.config import settings

celery_app = Celery(
    'dataforge',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        'tasks.job_tasks',
        'tasks.file_tasks',
    ],
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        'tasks.file_tasks.process_text_file': {'queue': 'fast_queue'},
        'tasks.file_tasks.process_image_file': {'queue': 'slow_queue'},
        'tasks.file_tasks.process_audio_file': {'queue': 'slow_queue'},
        'tasks.job_tasks.postprocess_dataset': {'queue': 'postprocess_queue'},
    },
)

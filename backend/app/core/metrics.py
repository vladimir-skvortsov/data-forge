from prometheus_client import Counter, Gauge, Histogram

jobs_total = Counter(
    'dataforge_jobs_total',
    'Total number of jobs by final status',
    ['status'],
)

files_processed_total = Counter(
    'dataforge_files_processed_total',
    'Total files processed by type and outcome',
    ['file_type', 'status'],
)

credits_charged_total = Counter(
    'dataforge_credits_charged_total',
    'Total credits charged across all completed jobs',
)

openrouter_api_errors_total = Counter(
    'dataforge_openrouter_api_errors_total',
    'Total errors returned by the OpenRouter API',
)

job_processing_duration_seconds = Histogram(
    'dataforge_job_processing_duration_seconds',
    'End-to-end job processing duration in seconds',
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

celery_queue_length = Gauge(
    'dataforge_celery_queue_length',
    'Current approximate number of tasks waiting in each Celery queue',
    ['queue'],
)

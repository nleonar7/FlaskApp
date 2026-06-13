"""Celery task definitions.

Tasks defined here are auto-discovered by `flaskblog.celery_app`.
Phase 1 will add the first real task: `scrape_source(source_name, region)`.
"""

from flaskblog.celery_app import celery


@celery.task(name='flaskblog.tasks.ping')
def ping():
    return 'pong'

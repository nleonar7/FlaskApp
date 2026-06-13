"""Celery instance wired to the Flask app.

Worker:
    celery -A flaskblog.celery_app worker --loglevel=info
Beat:
    celery -A flaskblog.celery_app beat --loglevel=info
"""

from celery import Celery

from flaskblog import app as flask_app


def _make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND'],
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    celery.autodiscover_tasks(['flaskblog'], related_name='tasks')
    return celery


celery = _make_celery(flask_app)

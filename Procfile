web: gunicorn flaskblog:app
worker: celery -A flaskblog.celery_app worker --loglevel=info
beat: celery -A flaskblog.celery_app beat --loglevel=info
release: flask db upgrade
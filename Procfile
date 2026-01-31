web: gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers=2 --threads=4 --worker-class=gthread --timeout=120
worker: celery -A app.celery worker --loglevel=info --concurrency=2
beat: celery -A app.celery beat --loglevel=info

#!/bin/bash
echo "=== Starting EduTutor ==="

# Apply database migrations on startup
flask db upgrade || echo "Migration failed or already applied"

# Start the application
exec gunicorn wsgi:app \
    --bind 0.0.0.0:$PORT \
    --workers=2 \
    --threads=4 \
    --worker-class=gthread \
    --timeout=120 \
    --access-logfile - \
    --error-logfile -

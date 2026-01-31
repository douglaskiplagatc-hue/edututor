#!/bin/bash
echo "=== Building EduTutor on Render ==="

# Install Python dependencies
pip install -r requirements.txt

# Install gunicorn if not in requirements
pip install gunicorn

# Run database migrations
flask db upgrade || echo "No migrations to run"

echo "=== Build complete ==="

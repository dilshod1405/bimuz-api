#!/bin/bash
set -e

echo "Waiting for database to be ready..."

until python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bimuz.settings')
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    connection.close()
except Exception:
    exit(1)
" 2>/dev/null; do
    echo "Database is unavailable - sleeping"
    sleep 1
done

echo "Database is ready!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 bimuz.wsgi:application

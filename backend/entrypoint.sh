#!/bin/sh
set -e

python manage.py wait_for_db
python manage.py migrate --noinput

exec gunicorn --bind "0.0.0.0:${BACKEND_PORT}" --workers "${GUNICORN_WORKERS}" conduit.wsgi:application

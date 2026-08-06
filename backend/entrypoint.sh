#!/bin/sh
set -e

while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
  echo "PostgreSQL not ready - sleeping for 1 second"
  sleep 1
done
echo "PostgreSQL is ready."

python manage.py migrate --noinput

exec gunicorn --bind "0.0.0.0:${BACKEND_PORT}" --workers "${GUNICORN_WORKERS}" conduit.wsgi:application

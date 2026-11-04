#!/bin/sh

set -e

cd /app/backend

python manage.py migrate --noinput

gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
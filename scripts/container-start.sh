#!/bin/sh
set -eu
: "${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY is required}"
python manage.py migrate --noinput
exec python serve.py --host 0.0.0.0 --port 8000

#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Compiling messages..."
python manage.py compilemessages

exec "$@"
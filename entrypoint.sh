#!/bin/sh
set -e

# This same image is used for the web process and the celery worker/beat
# processes (just with a different CMD). Migrations/static/messages only
# need to run once, from the web process — running them again from every
# celery container would race the web container's run on every deploy.
if [ "$1" = "gunicorn" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    echo "Compiling messages..."
    python manage.py compilemessages
fi

exec "$@"
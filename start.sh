#!/bin/bash

/venv/amy/bin/python manage.py check --fail-level WARNING

/venv/amy/bin/python manage.py migrate

/venv/amy/bin/python manage.py createcachetable

/venv/amy/bin/gunicorn \
    --workers=4 \
    --bind=0.0.0.0:8000 \
    --env DJANGO_SETTINGS_MODULE=config.settings \
    config.wsgi
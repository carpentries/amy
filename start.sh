#!/bin/bash

pipenv run python manage.py check --fail-level WARNING

pipenv run python manage.py migrate

pipenv run python manage.py createcachetable

pipenv run gunicorn \
    --workers=4 \
    --bind=0.0.0.0:8000 \
    --env DJANGO_SETTINGS_MODULE=config.settings \
    config.wsgi

#!/bin/bash

uv run python manage.py check --fail-level WARNING

uv run python manage.py migrate

uv run python manage.py createcachetable

uv run python manage.py runscript seed_badges
uv run python manage.py runscript seed_communityroles
uv run python manage.py runscript seed_training_requirements
uv run python manage.py runscript seed_involvements
uv run python manage.py runscript seed_emails
uv run python manage.py runscript seed_event_categories
uv run python manage.py runscript seed_benefits

uv run python manage.py create_superuser

uv run gunicorn \
    --workers=4 \
    --bind=0.0.0.0:80 \
    --access-logfile - \
    --capture-output \
    --env DJANGO_SETTINGS_MODULE=config.settings \
    config.wsgi

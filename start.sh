#!/bin/bash

/venv/amy/bin/python manage.py check --fail-level WARNING

/venv/amy/bin/python manage.py migrate

/venv/amy/bin/python manage.py createcachetable

/venv/amy/bin/python manage.py runscript seed_autoemails
/venv/amy/bin/python manage.py runscript seed_communityroles
/venv/amy/bin/python manage.py runscript seed_badges
/venv/amy/bin/python manage.py runscript seed_training_requirements

/venv/amy/bin/python manage.py create_superuser --random-password

/venv/amy/bin/gunicorn \
    --workers=4 \
    --bind=0.0.0.0:80 \
    --access-logfile - \
    --capture-output \
    --env DJANGO_SETTINGS_MODULE=config.settings \
    config.wsgi

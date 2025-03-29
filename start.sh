#!/bin/bash

ls -l /root/.local/bin
/root/.local/bin/poetry run python manage.py check --fail-level WARNING

/root/.local/bin/poetry run python manage.py migrate

/root/.local/bin/poetry run python manage.py createcachetable

/root/.local/bin/poetry run python manage.py runscript seed_badges
/root/.local/bin/poetry run python manage.py runscript seed_communityroles
/root/.local/bin/poetry run python manage.py runscript seed_training_requirements
/root/.local/bin/poetry run python manage.py runscript seed_involvements
/root/.local/bin/poetry run python manage.py runscript seed_emails

/root/.local/bin/poetry run python manage.py create_superuser

/root/.local/bin/poetry run gunicorn \
    --workers=4 \
    --bind=0.0.0.0:80 \
    --access-logfile - \
    --capture-output \
    --env DJANGO_SETTINGS_MODULE=config.settings \
    config.wsgi

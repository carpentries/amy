#!/bin/bash

set -e

DJANGODIR=/home/amy/amy
VIRTUALENV=/home/amy/amy/venv
NUM_WORKERS=2

export DJANGO_SETTINS_MODULE=amy.settings
export PYTHONPATH=${DJANGODIR}:${PYTHONPATH}

cd ${DJANGODIR}

exec ${VIRTUALENV}/bin/gunicorn amy.wsgi:application \
    --workers ${NUM_WORKERS} \
    --user=amy \
    --group=amy \
    --name=amy \
    --bind 127.0.0.1:8000

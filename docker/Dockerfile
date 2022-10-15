# $ GIT_COMMIT=$(git rev-parse --short HEAD)
# $ docker build -t amy:latest --label commit=$GIT_COMMIT -f docker/Dockerfile .

# ----------------------------------
FROM python:3.9-slim-buster as base

# security updates; libpq5 is required in runtime by psycopg2
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends libpq5

# ----------------------------------
FROM base AS compilation

# some dependencies require compilation
# TODO: remove compilation dependencies:
#       * use psycopg2-binary instead of psycopg2 (gcc+libpq-dev required)
RUN apt-get install -y --no-install-recommends gcc libpq-dev \
    && python3 -m pip install pipenv \
    && mkdir /app

# venv will exist in /app/.venv
ENV PIPENV_VENV_IN_PROJECT=true
WORKDIR /app
COPY ./Pipfile* .
# install runtime dependencies
RUN pipenv sync

COPY . .

# ----------------------------------
FROM base AS release

COPY --from=compilation /app /app
WORKDIR /app

EXPOSE 80
CMD .venv/bin/python ./manage.py runserver 0.0.0.0:80

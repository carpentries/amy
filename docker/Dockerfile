# $ GIT_COMMIT=$(git rev-parse --short HEAD)
# $ docker build -t amy:latest -t amy:$GIT_COMMIT --label commit=$GIT_COMMIT -f docker/Dockerfile .

# ----------------------------------
FROM python:3.11-slim-bullseye as base

# security updates
RUN apt-get update && apt-get -y upgrade && apt-get install -y --no-install-recommends libpq5

# ----------------------------------
FROM base AS dependencies

RUN mkdir /app
RUN apt-get install -y --no-install-recommends libpq-dev gcc libstdc++-10-dev
RUN python3 -m pip install pipenv

# venv will exist in /app/.venv
ENV PIPENV_VENV_IN_PROJECT=true
WORKDIR /app
COPY ./Pipfile* .

# install runtime dependencies
RUN pipenv sync

COPY . .

# ----------------------------------
FROM base AS release

COPY --from=dependencies /app /app
WORKDIR /app

EXPOSE 8000
CMD .venv/bin/gunicorn --workers=4 --bind=0.0.0.0:8000 --env DJANGO_SETTINGS_MODULE=config.settings config.wsgi

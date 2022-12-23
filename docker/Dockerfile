# $ GIT_COMMIT=$(git rev-parse --short HEAD)
# $ docker build -t amy:latest -t amy:$GIT_COMMIT --label commit=$GIT_COMMIT -f docker/Dockerfile .

# ----------------------------------
# BASE IMAGE: slim debian bullseye
# ----------------------------------
FROM python:3.11-slim-bullseye as base

# security updates
RUN apt-get update && apt-get -y upgrade && apt-get install -y --no-install-recommends libpq5


# ----------------------------------
# PYTHON DEPENDENCIES INSTALLATION
# ----------------------------------
FROM base AS dependencies

RUN apt-get install -y --no-install-recommends libpq-dev gcc libstdc++-10-dev
RUN python3 -m pip install pipenv
RUN mkdir /app
RUN mkdir /venv

# venv will exist under `/venv/amy`
ENV PIPENV_DONT_LOAD_ENV=true
ENV PIPENV_VENV_IN_PROJECT=false
ENV PIPENV_CUSTOM_VENV_NAME=amy
ENV WORKON_HOME=/venv
WORKDIR /app
COPY . .

# install runtime dependencies
RUN pipenv sync


# ----------------------------------
# NODE DEPENDENCIES INSTALLATION
# ----------------------------------
FROM node:18-bullseye-slim AS node_dependencies
RUN mkdir /app

WORKDIR /app
COPY . .

# install front-end dependencies
RUN npm install


# ----------------------------------
# COPYING STATICFILES INTO FINAL DESTINATION
# ----------------------------------
FROM base AS staticfiles

COPY --from=dependencies /venv /venv
COPY --from=dependencies /app /app
COPY --from=node_dependencies /app/node_modules /app/node_modules

ENV DJANGO_SETTINGS_MODULE=config.settings
WORKDIR /app
RUN /venv/amy/bin/python manage.py collectstatic --no-input


# ----------------------------------
# RELEASE STAGE
# ----------------------------------
FROM base AS release

COPY --from=dependencies /venv /venv
COPY --from=staticfiles /app /app
COPY --from=node_dependencies /app/node_modules /app/node_modules

WORKDIR /app
EXPOSE 80

ENV PATH="${PATH}:/venv/amy/bin"
CMD ./start.sh

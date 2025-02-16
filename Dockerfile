# $ GIT_COMMIT=$(git rev-parse --short HEAD)
# $ docker build -t amy:latest -t amy:$GIT_COMMIT --label commit=$GIT_COMMIT .

# ----------------------------------
# BASE IMAGE: slim debian bullseye
# ----------------------------------
FROM python:3.12-slim AS base

# security updates
RUN apt-get update && apt-get -y upgrade && apt-get install -y --no-install-recommends libpq5


# ----------------------------------
# PYTHON DEPENDENCIES INSTALLATION
# ----------------------------------
FROM base AS dependencies

RUN apt-get install -y --no-install-recommends libpq-dev gcc
RUN python3 -m pip install pipx
RUN python3 -m pipx ensurepath
RUN pipx install poetry==2.0.0
RUN mkdir /app
RUN mkdir /venv

# venv will exist under `/venv/...`
ENV POETRY_VIRTUALENVS_PATH=/venv
WORKDIR /app
COPY . .

# install runtime dependencies
RUN /root/.local/bin/poetry sync
# RUN /root/.local/bin/poetry config --list && exit 1


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

COPY --from=dependencies /root/.local/share/pipx/venvs /root/.local/share/pipx/venvs
COPY --from=dependencies /root/.local/bin /root/.local/bin
COPY --from=dependencies /venv /venv
COPY --from=dependencies /app /app
COPY --from=node_dependencies /app/node_modules /app/node_modules

ENV DJANGO_SETTINGS_MODULE=config.settings
ENV POETRY_VIRTUALENVS_PATH=/venv
WORKDIR /app
RUN /root/.local/bin/poetry run python manage.py collectstatic --no-input


# ----------------------------------
# RELEASE STAGE
# ----------------------------------
FROM base AS release

COPY --from=dependencies /root/.local/share/pipx/venvs /root/.local/share/pipx/venvs
COPY --from=dependencies /root/.local/bin /root/.local/bin
COPY --from=dependencies /venv /venv
COPY --from=staticfiles /app /app
COPY --from=node_dependencies /app/node_modules /app/node_modules

WORKDIR /app
EXPOSE 80

ENV DJANGO_SETTINGS_MODULE=config.settings
ENV POETRY_VIRTUALENVS_PATH=/venv
ENV PATH="${PATH}:/root/.local/bin/"
RUN chmod +x ./start.sh
CMD ["./start.sh"]

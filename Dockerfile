# $ GIT_COMMIT=$(git rev-parse --short HEAD)
# $ docker build -t amy:latest -t amy:$GIT_COMMIT --label commit=$GIT_COMMIT .

# ----------------------------------
# BASE IMAGE: slim debian bullseye
# ----------------------------------
FROM python:3.14-slim AS base

# security updates
RUN apt-get update && apt-get -y upgrade && apt-get install -y --no-install-recommends \
  libpq5 libcairo2 libjpeg-dev libffi-dev zlib1g-dev
# fonts for the SVG generation
RUN apt-get install -y fonts-liberation


# ----------------------------------
# PYTHON DEPENDENCIES INSTALLATION
# ----------------------------------
FROM base AS dependencies

RUN apt-get install -y --no-install-recommends libpq-dev gcc
RUN python3 -m pip install pipx
RUN python3 -m pipx ensurepath
RUN pipx install uv
RUN mkdir /app
WORKDIR /app
COPY . .

# install runtime dependencies
RUN /root/.local/bin/uv sync


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
COPY --from=dependencies /app /app
COPY --from=node_dependencies /app/node_modules /app/node_modules

ENV DJANGO_SETTINGS_MODULE=config.settings
WORKDIR /app
RUN /root/.local/bin/uv run python manage.py collectstatic --no-input


# ----------------------------------
# RELEASE STAGE
# ----------------------------------
FROM base AS release

COPY --from=dependencies /root/.local/share/pipx/venvs /root/.local/share/pipx/venvs
COPY --from=dependencies /root/.local/bin /root/.local/bin
COPY --from=staticfiles /app /app
COPY --from=node_dependencies /app/node_modules /app/node_modules

WORKDIR /app
EXPOSE 80

ENV DJANGO_SETTINGS_MODULE=config.settings
ENV PATH="${PATH}:/root/.local/bin/"
RUN chmod +x ./start.sh
CMD ["./start.sh"]

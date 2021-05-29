FROM python:3.9-slim-buster as base

# `.` is for the current build context
# use this command to build (from project root):
# $ GIT_COMMIT=$(git rev-parse --short HEAD)
# $ docker build -t amy:latest --label commit=$GIT_COMMIT -f docker/Dockerfile .

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc libpq-dev python3-dev

RUN python3 -m venv /venv
RUN /venv/bin/pip3 install pipenv

RUN mkdir /app
WORKDIR /app
COPY ./Pipfile* .
RUN /venv/bin/pipenv sync

COPY . /app

FROM base AS release

COPY --from=base /venv /venv

EXPOSE 80

CMD /venv/bin/pipenv run ./manage.py runserver 0.0.0.0:80

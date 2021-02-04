FROM python:3.8-alpine as base


# `.` is for the current build context
# use this command to build (from project root):
# docker build -t amy:latest -f docker/Dockerfile .

ENV INSTALL_PATH /amy
RUN mkdir -p $INSTALL_PATH

COPY ./requirements.txt /app/requirements.txt

RUN apk update
RUN apk add --no-cache postgresql-dev
RUN apk add --no-cache --virtual .build-deps \
    python3-dev gcc g++ unixodbc-dev linux-headers \
    libffi-dev jpeg-dev zlib-dev \
    && pip3 install --upgrade pip \
    && pip3 install -r /app/requirements.txt --no-cache \
    && apk del --no-cache .build-deps


COPY . /app

WORKDIR $INSTALL_PATH

FROM base AS release

EXPOSE 80

CMD python manage.py runserver 0.0.0.0:80

FROM python:3.7-alpine

RUN apk update && apk add build-base python3-dev \
    # argon2 dependency
    libffi-dev \
    # Pillow dependencies
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    harfbuzz-dev \
    fribidi-dev

ENV INSTALL_PATH /amy
RUN mkdir -p $INSTALL_PATH

WORKDIR $INSTALL_PATH

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD python manage.py runserver 0.0.0.0:8000
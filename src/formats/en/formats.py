# Based on https://github.com/django/django/blob/main/django/conf/locale/en/formats.py
# Turns out that localized formats have higher priority than setting the format in the
# settings.py file.
TIME_FORMAT = "P e"
DATETIME_FORMAT = "N j, Y, P e"

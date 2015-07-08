# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

AIRPORTS = [
    ('ALC', 'Alicante', 'ES', 38.2821999, -0.558156),
    ('ARB', 'Ann Arbor, MI', 'US', 42.2229996, -83.7455978),
    ('BGR', 'Bangor, ME', 'US', 44.8073997, -68.8281021),
    ('CVG', 'Cincinnati, KY', 'US', 39.0488014, -84.6678009),
    ('DAY', 'James M. Cox Dayton, OH', 'US', 39.902401, -84.2193985),
    ('GLE', 'Gainesville, TX', 'US', 33.651389, -97.196944),
    ('GNV', 'Gainesville, FL', 'US', 29.69, -82.271667),
    ('GRU', 'Sao Paulo Guarulhos', 'BR', -23.435556, -46.473056),
    ('GSP', 'Greenville Spartanburg, SC', 'US', 34.8956985, -82.2189026),
    ('ROA', 'Roanoke Blacksburg, VA', 'US', 37.3255005, -79.9754028),
    ('XNA', 'Fayetteville Springdale, AR', 'US', 36.2818985, -94.3068008),
    ('YQM', 'Moncton', 'CA', 46.1122017, -64.6785965),
    ('YTZ', 'Billy Bishop Toronto', 'CA', 43.6274986, -79.3962021),
]


def add_bunch_of_new_airports(apps, schema_editor):
    Airport = apps.get_model('workshops', 'Airport')
    for iata, fullname, country, latitude, longitude in AIRPORTS:
        Airport.objects.get_or_create(iata=iata, fullname=fullname,
                                      country=country, latitude=latitude,
                                      longitude=longitude)


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0025_auto_20150707_0809'),
    ]

    operations = [
        migrations.RunPython(add_bunch_of_new_airports),
    ]

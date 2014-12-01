from django.db import models

class Airport(models.Model):
    '''Represent an airport (used to locate instructors).'''

    iata      = models.CharField(max_length=3)
    fullname  = models.CharField(max_length=100)
    country   = models.CharField(max_length=100)
    latitude  = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.iata

from django.db import models

#------------------------------------------------------------

STR_LEN = 100         # length of long strings

#------------------------------------------------------------

class Site(models.Model):
    '''Represent a site where workshops are hosted.'''

    domain    = models.CharField(max_length=STR_LEN, unique=True)
    fullname  = models.CharField(max_length=STR_LEN, unique=True)
    country   = models.CharField(max_length=STR_LEN)

    def __str__(self):
        return self.domain

#------------------------------------------------------------

class Airport(models.Model):
    '''Represent an airport (used to locate instructors).'''

    iata      = models.CharField(max_length=3, unique=True)
    fullname  = models.CharField(max_length=STR_LEN, unique=True)
    country   = models.CharField(max_length=STR_LEN)
    latitude  = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.iata

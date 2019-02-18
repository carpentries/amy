from django.db import models
from django_countries.fields import CountryField


class Criterium(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Name",
        blank=False,
        unique=True,
    )
    countries = CountryField(
        multiple=True,
        verbose_name="Countries to match this criterium"
    )
    email = models.EmailField(
        verbose_name='Notification email address',
        blank=False,
    )

    class Meta:
        ordering = ['name', 'email']
        verbose_name = 'Notification Criterium'
        verbose_name_plural = 'Notification Criteria'

    def __str__(self):
        return "Criterium {name} ({email})".format(name=self.name,
                                                   email=self.email)


class Continent(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Name",
        blank=False,
        unique=True,
    )
    countries = CountryField(
        multiple=True,
        verbose_name="Countries in this continent"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Continent'
        verbose_name_plural = 'Continents'

    def __str__(self):
        return "Continent {name}".format(name=self.name)

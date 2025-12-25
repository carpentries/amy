from django.contrib import admin

from .models import Continent, Criterium


class CriteriumAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "get_countries")

    def get_countries(self, obj):
        if len(obj.countries) > 10:
            return ", ".join([x.name for x in obj.countries[:10]]) + "..."
        else:
            return ", ".join([x.name for x in obj.countries])

    get_countries.short_description = "Matching countries"
    get_countries.admin_order_field = "countries"


class ContinentAdmin(admin.ModelAdmin):
    list_display = ("name", "get_countries")

    def get_countries(self, obj):
        if len(obj.countries) > 10:
            return ", ".join([x.name for x in obj.countries[:10]]) + "..."
        else:
            return ", ".join([x.name for x in obj.countries])

    get_countries.short_description = "Matching countries"
    get_countries.admin_order_field = "countries"


admin.site.register(Criterium, CriteriumAdmin)
admin.site.register(Continent, ContinentAdmin)

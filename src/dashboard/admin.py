from django.contrib import admin

from .models import Continent, Criterium


class CriteriumAdmin(admin.ModelAdmin[Criterium]):
    list_display = ("name", "email", "get_countries")

    def get_countries(self, obj: Criterium) -> str:
        if len(obj.countries) > 10:
            return ", ".join([x.name for x in obj.countries[:10]]) + "..."
        else:
            return ", ".join([x.name for x in obj.countries])

    get_countries.short_description = "Matching countries"  # type: ignore[attr-defined]
    get_countries.admin_order_field = "countries"  # type: ignore[attr-defined]


class ContinentAdmin(admin.ModelAdmin[Continent]):
    list_display = ("name", "get_countries")

    def get_countries(self, obj: Continent) -> str:
        if len(obj.countries) > 10:
            return ", ".join([x.name for x in obj.countries[:10]]) + "..."
        else:
            return ", ".join([x.name for x in obj.countries])

    get_countries.short_description = "Matching countries"  # type: ignore[attr-defined]
    get_countries.admin_order_field = "countries"  # type: ignore[attr-defined]


admin.site.register(Criterium, CriteriumAdmin)
admin.site.register(Continent, ContinentAdmin)

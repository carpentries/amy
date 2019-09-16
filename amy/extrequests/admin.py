from django.contrib import admin

from extrequests.models import (
    DataAnalysisLevel,
    DCWorkshopDomain,
    DCWorkshopTopic,
    DataVariant,
)


admin.site.register(DataAnalysisLevel)
admin.site.register(DCWorkshopDomain)
admin.site.register(DCWorkshopTopic)
admin.site.register(DataVariant)

from django.contrib import admin

from .models import (
    Tag,
    AcademicLevel,
    ComputingExperienceLevel,
    DataAnalysisLevel,
    Role,
    Lesson,
    KnowledgeDomain,
    Badge,
)


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'verbose_name')


admin.site.register(Tag)
admin.site.register(AcademicLevel)
admin.site.register(ComputingExperienceLevel)
admin.site.register(DataAnalysisLevel)
admin.site.register(Role, RoleAdmin)
admin.site.register(Lesson)
admin.site.register(KnowledgeDomain)
admin.site.register(Badge)

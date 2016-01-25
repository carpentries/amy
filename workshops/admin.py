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

admin.site.register(Tag)
admin.site.register(AcademicLevel)
admin.site.register(ComputingExperienceLevel)
admin.site.register(DataAnalysisLevel)
admin.site.register(Role)
admin.site.register(Lesson)
admin.site.register(KnowledgeDomain)
admin.site.register(Badge)

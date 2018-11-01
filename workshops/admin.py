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
    TrainingRequirement,
    TrainingRequest,
    Curriculum,
)


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'verbose_name')


class CurriculumAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'slug', 'name', 'active', 'unknown')


admin.site.register(Tag)
admin.site.register(AcademicLevel)
admin.site.register(ComputingExperienceLevel)
admin.site.register(DataAnalysisLevel)
admin.site.register(Role, RoleAdmin)
admin.site.register(Lesson)
admin.site.register(KnowledgeDomain)
admin.site.register(Badge)
admin.site.register(TrainingRequirement)
admin.site.register(TrainingRequest)
admin.site.register(Curriculum, CurriculumAdmin)

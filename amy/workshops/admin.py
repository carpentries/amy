from django.contrib import admin

from workshops.models import (
    AcademicLevel,
    ComputingExperienceLevel,
)
from workshops.models import (
    Tag,
    Role,
    Lesson,
    KnowledgeDomain,
    Badge,
    TrainingRequirement,
    TrainingRequest,
    Curriculum,
    InfoSource,
)


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'verbose_name')


class CurriculumAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'carpentry', 'slug', 'name', 'description',
                    'active', 'other', 'unknown')


class InfoSourceAdmin(admin.ModelAdmin):
    list_display = ('name', )


admin.site.register(AcademicLevel)
admin.site.register(ComputingExperienceLevel)

admin.site.register(Tag)
admin.site.register(Role, RoleAdmin)
admin.site.register(Lesson)
admin.site.register(KnowledgeDomain)
admin.site.register(Badge)
admin.site.register(TrainingRequirement)
admin.site.register(TrainingRequest)
admin.site.register(Curriculum, CurriculumAdmin)
admin.site.register(InfoSource, InfoSourceAdmin)

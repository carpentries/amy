from django.contrib import admin

from workshops.models import (
    AcademicLevel,
    Badge,
    ComputingExperienceLevel,
    Curriculum,
    InfoSource,
    KnowledgeDomain,
    Lesson,
    MemberRole,
    Role,
    Tag,
    TrainingRequest,
    TrainingRequirement,
)


class MemberRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "verbose_name")


class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "verbose_name")


class CurriculumAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "carpentry",
        "slug",
        "name",
        "description",
        "website",
        "active",
        "other",
        "unknown",
        "mix_match",
    )


class InfoSourceAdmin(admin.ModelAdmin):
    list_display = ("name",)


class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "priority", "details")


admin.site.register(MemberRole, MemberRoleAdmin)

admin.site.register(AcademicLevel)
admin.site.register(ComputingExperienceLevel)

admin.site.register(Tag, TagAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Lesson)
admin.site.register(KnowledgeDomain)
admin.site.register(Badge)
admin.site.register(TrainingRequirement)
admin.site.register(TrainingRequest)
admin.site.register(Curriculum, CurriculumAdmin)
admin.site.register(InfoSource, InfoSourceAdmin)

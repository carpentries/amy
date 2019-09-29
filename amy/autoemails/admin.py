from django.contrib import admin


from .models import EmailTemplate


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['slug', 'subject', 'to_header', 'from_header']


admin.site.register(EmailTemplate, EmailTemplateAdmin)

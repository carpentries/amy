from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
]

urlpatterns = format_suffix_patterns(urlpatterns)  # allow to specify format

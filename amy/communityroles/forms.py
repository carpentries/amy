from django import forms

from workshops.fields import ModelSelect2Widget
from workshops.forms import SELECT2_SIDEBAR, BootstrapHelper, WidgetOverrideMixin

from .models import CommunityRole


class CommunityRoleForm(WidgetOverrideMixin, forms.ModelForm):
    class Meta:
        model = CommunityRole
        fields = (
            "config",
            "person",
            "award",
            "start",
            "end",
            "inactivation",
            "membership",
            "url",
            "generic_relation_m2m",
        )
        widgets = {
            "person": ModelSelect2Widget(
                data_view="person-lookup", attrs=SELECT2_SIDEBAR
            ),
            "award": ModelSelect2Widget(
                data_view="award-lookup", attrs=SELECT2_SIDEBAR
            ),
            "membership": ModelSelect2Widget(
                data_view="membership-lookup", attrs=SELECT2_SIDEBAR
            ),
        }

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        super().__init__(*args, **kwargs)
        bootstrap_kwargs = {
            "add_cancel_button": False,
            "form_tag": form_tag,
        }
        self.helper = BootstrapHelper(**bootstrap_kwargs)

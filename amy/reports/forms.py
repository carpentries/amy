from django import forms

from workshops.forms import BootstrapHelper


class DebriefForm(forms.Form):
    '''Represent general debrief form.'''
    begin_date = forms.DateField(
        label='Begin date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ]
    )
    end_date = forms.DateField(
        label='End date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ]
    )

    MODE_CHOICES = (
        ('all', 'List all events'),
        ('TTT', 'List only TTT events'),
        ('nonTTT', 'List only non-TTT events'),
    )
    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        widget=forms.RadioSelect,
        initial='all',
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)


class AllActivityOverTimeForm(forms.Form):
    start = forms.DateField(
        label='Begin date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ],
    )
    end = forms.DateField(
        label='End date',
        help_text='YYYY-MM-DD',
        input_formats=['%Y-%m-%d', ],
    )

    helper = BootstrapHelper(use_get_method=True, add_cancel_button=False)

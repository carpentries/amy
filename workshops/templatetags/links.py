import re

from django import template

register = template.Library()

REPO_REGEXP = re.compile(r'https://github\.com/(?P<name>\S+)/(?P<repo>\S+)/?')
REPO_SCHEMA = 'https://github.com/{name}/{repo}/'
WEBSITE_REGEXP = re.compile(
    r'http://(?P<name>\S+)\.github\.(io|com)/(?P<repo>\S+)/?'
)
WEBSITE_SCHEMA = 'http://{name}.github.io/{repo}/'


@register.assignment_tag
def format_link_to_repository(link):
    """
    Use: {% format_link_to_repository event.url as repo_link %}
    Then: {{ repo_link|urlize|default_if_none:"—" }}
    """
    if not link:
        return link
    elif REPO_REGEXP.match(link):
        return link
    else:
        try:
            repository = WEBSITE_REGEXP.findall(link)[0]
            return REPO_SCHEMA.format(name=repository[0], repo=repository[-1])
        except IndexError:
            return link


@register.assignment_tag
def format_link_to_website(link):
    """
    Use: {% format_link_to_website event.url as website_link %}
    Then: {{ website_link|urlize|default_if_none:"—" }}
    """
    if not link:
        return link
    elif WEBSITE_REGEXP.match(link):
        return link
    else:
        try:
            site = REPO_REGEXP.findall(link)[0]
            return WEBSITE_SCHEMA.format(name=site[0], repo=site[-1])
        except IndexError:
            return link

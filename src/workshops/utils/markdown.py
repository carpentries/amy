import markdown
import nh3
from django.utils.safestring import SafeString, mark_safe

ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def render_markdown(text: str) -> SafeString:
    """Render Markdown to HTML and sanitize the result.

    Python-Markdown passes raw HTML through, so the output must be cleaned before
    it's marked as safe for use in templates."""
    html = markdown.markdown(text)
    return mark_safe(nh3.clean(html, url_schemes=ALLOWED_URL_SCHEMES))

"""Template filters for showing user-written round text."""

from django import template
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

register = template.Library()

FSI, PDI = chr(0x2068), chr(0x2069)
# U+202A to U+202E and U+2066 to U+2069, removed from page titles.
BIDI_CONTROLS = dict.fromkeys([*range(0x202A, 0x202F), *range(0x2066, 0x206A)])


@register.filter
def title_isolate(text):
    """Drop bidi controls, join lines with spaces and wrap it in FSI ... PDI.

    A paragraph separator such as U+2029 would end the isolate, so none stays.
    """
    lines = str(text).translate(BIDI_CONTROLS).splitlines()
    return FSI + " ".join(lines) + PDI


@register.filter
def isolated_lines(text):
    """Escape each line into its own dir="auto" span, joined by <br>.

    Splitting at every `str.splitlines()` separator keeps paragraph separators
    such as U+2029 out of the page, so each line's direction stays isolated.
    """
    lines = ((line,) for line in str(text).splitlines())
    return format_html_join(mark_safe("<br>"), '<span dir="auto">{}</span>', lines)

"""Template filters for showing user-written round text."""

from django import template

register = template.Library()

# U+202A to U+202E and U+2066 to U+2069, removed from page titles.
BIDI_CONTROLS = dict.fromkeys([*range(0x202A, 0x202F), *range(0x2066, 0x206A)])


@register.filter
def title_isolate(text):
    """Drop bidi controls and wrap the text in FSI ... PDI for a <title>."""
    return "\u2068" + str(text).translate(BIDI_CONTROLS) + "\u2069"

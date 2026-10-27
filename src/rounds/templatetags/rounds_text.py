"""Template filters for showing user-written round text."""

import re

from django import template
from django.utils.html import conditional_escape, format_html, format_html_join
from django.utils.safestring import mark_safe

from rounds.forms import DIRECTION_CONTROLS

register = template.Library()

FSI, PDI = chr(0x2068), chr(0x2069)
# A str.translate table deleting the text-direction controls from page titles.
DROP_DIRECTION_CONTROLS = dict.fromkeys(map(ord, DIRECTION_CONTROLS))


@register.filter
def title_isolate(text):
    """Drop text-direction controls, join lines with spaces, wrap in FSI ... PDI.

    A paragraph separator such as U+2029 would end the isolate, so none stays.
    """
    lines = str(text).translate(DROP_DIRECTION_CONTROLS).splitlines()
    return FSI + " ".join(lines) + PDI


@register.filter
def isolated_lines(text):
    """Escape each line into its own dir="auto" span, joined by <br>.

    Splitting at every `str.splitlines()` separator keeps paragraph separators
    such as U+2029 out of the page, so each line's direction stays isolated.
    """
    lines = ((line,) for line in str(text).splitlines())
    return format_html_join(mark_safe("<br>"), '<span dir="auto">{}</span>', lines)


# The RND-5.1 message: fixed text around the label, which is the only user text.
RETEST = re.compile(
    r"(Retest requested for (?:1 test case|(?:[2-9]|[1-9][0-9]+) test cases)"
    r" on build )(.+)\.",
    re.DOTALL,
)


def retest_message(count, label):
    """The RND-5.1 success message for `count` distinct cases."""
    noun = "test case" if count == 1 else "test cases"
    return f"Retest requested for {count} {noun} on build {label}."


@register.filter
def status_message(message):
    """Show a message escaped, isolating a retest message's label by line.

    Only a message tagged `retest` whose whole text matches the fixed form is
    split; anything else is shown as plain escaped text.
    """
    text = str(message)
    found = RETEST.fullmatch(text) if "retest" in message.tags.split() else None
    if found is None:
        return conditional_escape(text)
    return format_html("{}{}.", found[1], isolated_lines(found[2]))

"""Round forms and the text field shared by every round text input."""

import unicodedata

from django import forms
from django.core.exceptions import ValidationError


def has_visible_character(text):
    """Return whether any character is not whitespace, control or format."""
    return any(
        not char.isspace() and unicodedata.category(char) not in ("Cc", "Cf")
        for char in text
    )


class RoundTextField(forms.CharField):
    """Trimmed text of 1 to `max_length` characters with a visible character."""

    def __init__(self, *, max_length, **kwargs):
        message = f"Enter 1 to {max_length} characters."
        super().__init__(
            max_length=max_length,
            error_messages={"required": message, "max_length": message},
            **kwargs,
        )

    def clean(self, value):
        """Apply Django's checks, including null characters, then visibility."""
        value = super().clean(value)
        if not has_visible_character(value):
            raise ValidationError(self.error_messages["required"], code="required")
        return value


class RoundForm(forms.Form):
    """A round's title, for creating and retitling a round."""

    title = RoundTextField(
        max_length=120, widget=forms.TextInput(attrs={"dir": "auto"})
    )

"""Round forms and the text field shared by every round text input."""

import unicodedata

from django import forms
from django.core.exceptions import ValidationError

from . import services
from .models import Criterion


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

    def to_python(self, value):
        """Count a browser's CR LF line break as one character, then trim."""
        if isinstance(value, str):
            value = value.replace("\r\n", "\n")
        return super().to_python(value)

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


def text_area():
    """A multi-line input whose direction follows its own text."""
    return forms.Textarea(attrs={"dir": "auto"})


class RecordForm(forms.Form):
    """A form for a record of `round_`, whose criteria are its only choices."""

    def __init__(self, round_, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "criteria" in self.fields:
            self.fields["criteria"].queryset = round_.criteria.all()


class CriterionForm(RecordForm):
    """An acceptance criterion's text."""

    text = RoundTextField(max_length=500, widget=text_area())


class CaseForm(RecordForm):
    """A test case's fields and the round's criteria it links to."""

    title = RoundTextField(
        max_length=120, widget=forms.TextInput(attrs={"dir": "auto"})
    )
    steps = RoundTextField(max_length=2000, widget=text_area())
    expected_result = RoundTextField(max_length=1000, widget=text_area())
    criteria = forms.ModelMultipleChoiceField(
        Criterion.objects.none(),
        label="Linked acceptance criteria",
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": services.NO_LINK,
            "invalid_choice": services.FOREIGN,
            "invalid_pk_value": services.FOREIGN,
        },
    )


class PublishForm(forms.Form):
    """The label of the build a Draft round is published on (RND-3)."""

    label = RoundTextField(
        max_length=100,
        label="Build label",
        widget=forms.TextInput(attrs={"dir": "auto"}),
    )

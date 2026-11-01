"""Round forms and the text field shared by every round text input."""

import unicodedata

from django import forms
from django.core.exceptions import ValidationError

from . import services
from .models import Build, Case, Criterion, Round

# The text-direction controls of rule 5: embeddings, overrides and their pop
# (U+202A to U+202E) and isolates (U+2066 to U+2069). They can reorder whole runs
# of text invisibly. The page-title filter strips the same set.
DIRECTION_CONTROLS = frozenset(
    map(chr, [*range(0x202A, 0x202F), *range(0x2066, 0x206A)])
)
DIRECTION_MESSAGE = "Hidden text-direction characters are not allowed."


def has_visible_character(text):
    """Return whether any character is not whitespace, control or format."""
    return any(
        not char.isspace() and unicodedata.category(char) not in ("Cc", "Cf")
        for char in text
    )


def limit(model, name):
    """Return a model field's `max_length`, so forms and storage share one limit."""
    return model._meta.get_field(name).max_length


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
        """Apply Django's checks, then the visibility and direction checks."""
        value = super().clean(value)
        if not has_visible_character(value):
            raise ValidationError(self.error_messages["required"], code="required")
        if not DIRECTION_CONTROLS.isdisjoint(value):
            raise ValidationError(DIRECTION_MESSAGE, code="direction_control")
        return value


class RoundForm(forms.Form):
    """A round's title, for creating and retitling a round."""

    title = RoundTextField(
        max_length=limit(Round, "title"), widget=forms.TextInput(attrs={"dir": "auto"})
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

    text = RoundTextField(max_length=limit(Criterion, "text"), widget=text_area())


class CaseForm(RecordForm):
    """A test case's fields and the round's criteria it links to."""

    title = RoundTextField(
        max_length=limit(Case, "title"), widget=forms.TextInput(attrs={"dir": "auto"})
    )
    steps = RoundTextField(max_length=limit(Case, "steps"), widget=text_area())
    expected_result = RoundTextField(
        max_length=limit(Case, "expected_result"), widget=text_area()
    )
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


def build_label():
    """A new build's "Build label" field, as long as a build's stored label."""
    return RoundTextField(
        max_length=limit(Build, "label"),
        label="Build label",
        widget=forms.TextInput(attrs={"dir": "auto"}),
    )


class PublishForm(forms.Form):
    """The label of the build a Draft round is published on (RND-3)."""

    label = build_label()


class RetestForm(forms.Form):
    """The cases of `round_` to test again and the new build's label (RND-5)."""

    cases = forms.ModelMultipleChoiceField(
        Case.objects.none(),
        label="Test cases to retest",
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": services.NO_CASE,
            "invalid_choice": services.FOREIGN_CASE,
            "invalid_pk_value": services.FOREIGN_CASE,
        },
    )
    label = build_label()

    def __init__(self, round_, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cases"].queryset = round_.cases.all()

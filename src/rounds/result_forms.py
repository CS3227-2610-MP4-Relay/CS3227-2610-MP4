"""Result-specific validation without changing shared round inputs (RES-2)."""

from django import forms

from .forms import (
    DIRECTION_CONTROLS,
    DIRECTION_MESSAGE,
    RoundTextField,
    has_visible_character,
    text_area,
)
from .models import Result


class ObservationField(RoundTextField):
    """Normalize round text, leaving optional/visible checks to the outcome."""

    def __init__(self):
        super().__init__(max_length=2000, required=False, widget=text_area())
        self.error_messages["max_length"] = "Enter at most 2000 characters."

    def clean(self, value):
        """Keep normalization, length and NUL validation; allow empty Pass."""
        return forms.CharField.clean(self, value)


class ResultForm(forms.Form):
    """Identical validation for saving a private draft or submitting it."""

    outcome = forms.ChoiceField(
        choices=[("", "---------"), *Result.Outcome.choices],
        error_messages={
            "required": "Choose Pass or Fail.",
            "invalid_choice": "Choose Pass or Fail.",
        },
    )
    observation = ObservationField()

    def clean(self):
        """Apply outcome-dependent visibility, direction and button checks."""
        cleaned = super().clean()
        text = cleaned.get("observation")
        if text is not None:
            fail = cleaned.get("outcome") == Result.Outcome.FAIL
            if (text or fail) and not has_visible_character(text):
                self.add_error(
                    "observation",
                    "Enter an observation for Fail."
                    if fail
                    else "Enter an observation with a visible character.",
                )
            elif not DIRECTION_CONTROLS.isdisjoint(text):
                self.add_error("observation", DIRECTION_MESSAGE)
        action = self.data.get("action")
        if action not in ("save", "submit"):
            self.add_error(None, "Choose Save draft or Submit.")
        cleaned["action"] = action
        return cleaned

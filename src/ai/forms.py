"""Form fields for the two RND-8 drafting routes."""

from django import forms

from rounds.models import Criterion
from rounds.services import FOREIGN


class DraftSelectForm(forms.Form):
    """The round's criteria to draft from, checked in creation order."""

    criteria = forms.ModelMultipleChoiceField(
        Criterion.objects.none(),
        label="Acceptance criteria to draft from",
        widget=forms.CheckboxSelectMultiple,
        required=False,
        error_messages={"invalid_choice": FOREIGN, "invalid_pk_value": FOREIGN},
    )

    def __init__(self, round_, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["criteria"].queryset = round_.criteria.all()

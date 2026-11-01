"""The criteria selection on the RND-8 drafting page."""

from django import forms

from rounds import services
from rounds.forms import RecordForm
from rounds.models import Criterion


class DraftSelectForm(RecordForm):
    """The round's criteria to draft from, checked in creation order."""

    criteria = forms.ModelMultipleChoiceField(
        Criterion.objects.none(),
        label="Acceptance criteria to draft from",
        widget=forms.CheckboxSelectMultiple,
        required=False,
        error_messages={
            "invalid_choice": services.FOREIGN,
            "invalid_pk_value": services.FOREIGN,
        },
    )

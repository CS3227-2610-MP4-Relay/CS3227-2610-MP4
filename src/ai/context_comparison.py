"""Fixed synthetic context pairs and structural observations (CTX-1)."""

import json
from dataclasses import dataclass

from django.views.decorators.debug import sensitive_variables

from . import drafting, feedback, gateway

CORPUS_VERSION = "context-1"
# Case/criterion prose visible to either role in the fictional inventory round.
BACKGROUND = {
    "visible_case_criteria": [
        "Dashboard cards sort by heading when Sort is selected. Check heading order.",
        "Profile colour changes update the preview. Check the preview colour.",
        "Archive navigation opens the archived list. Check the list heading.",
    ]
}


@dataclass(frozen=True)
class Case:
    """One immutable experiment request; never serialize source-bearing fields."""

    id: str
    feature: str
    arm: str
    instructions: str
    data: str


@sensitive_variables()
def corpus():
    """Freeze four rubric-aligned targets with alternating selected/broader arms."""
    targets = (
        (
            "drafting-boundary",
            (
                "A saved item name may contain 1–40 characters; an empty or "
                '41-character name shows "Enter 1 to 40 characters." and does not save.'
            ),
        ),
        (
            "drafting-state",
            (
                "Cancelling an unsaved item edit restores the last saved name "
                "and leaves the item unchanged."
            ),
        ),
        ("feedback-incomplete", "The CSV included the wrong rows."),
        (
            "feedback-complete",
            (
                "Opened Items in browser version 126 on desktop; applied Available; "
                "exported CSV; row Sample-2 marked Unavailable appeared; repeated "
                "these actions twice with the same row; expected only Available rows."
            ),
        ),
    )
    cases = []
    for index, (name, text) in enumerate(targets):
        feature = "drafting" if index < 2 else "feedback"
        if feature == "drafting":
            core = {"criteria": [{"label": "C1", "text": drafting.clean(text).strip()}]}
            instructions = drafting.INSTRUCTIONS
        else:
            core = json.loads(
                feedback.encode(
                    feedback.Source(
                        (0, "", text),
                        (
                            0,
                            "Export Available items",
                            "1. Open Items.\n2. Apply Available.\n3. Export CSV.",
                            "The CSV contains only Available rows.",
                        ),
                        (0, ""),
                        (
                            (
                                0,
                                (
                                    "The CSV export contains only Available rows "
                                    "when the Available filter is applied."
                                ),
                            ),
                        ),
                    )
                )
            )
            instructions = feedback.INSTRUCTIONS
        for arm in (
            ("selected", "broader") if index % 2 == 0 else ("broader", "selected")
        ):
            data = core if arm == "selected" else {**core, "background": BACKGROUND}
            cases.append(
                Case(
                    f"{name}-{arm}",
                    feature,
                    arm,
                    instructions,
                    json.dumps(data, ensure_ascii=False),
                )
            )
    return tuple(cases)


@sensitive_variables()
def score(case, result):
    """Observe schema acceptance and validated counts without grading semantics."""
    status = (
        "success"
        if isinstance(result, gateway.Success)
        else "refused"
        if isinstance(result, gateway.Refused)
        else "failed"
        if isinstance(result, gateway.Failed)
        else "unattempted"
    )
    usage = gateway._checked_usage(result.usage) if result is not None else None
    row = {
        "id": case.id,
        "status": status,
        "schema_accepted": None,
        "accepted_items": None,
        **{field: getattr(usage, field, None) for field in gateway.TOKEN_FIELDS},
    }
    if status == "success":
        try:
            parsed = (
                drafting.parse(result.text, ["C1"])
                if case.feature == "drafting"
                else feedback.parse(result.text)
            )
        except drafting.InvalidReply:
            row["schema_accepted"] = False
        else:
            row.update(schema_accepted=True, accepted_items=len(parsed))
    return row

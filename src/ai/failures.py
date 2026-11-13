"""Fixed user messages for gateway refusals with a known cause (RND-8.10, RES-4.10)."""

from . import gateway

BUSY = "The AI service is busy. Try again in a minute."
OWN_QUOTA = "You have used your AI allowance for this hour. Try again later."
SHARED_QUOTA = "The shared AI allowance is used up for now. Try again later."
CAUSES = {
    "busy": BUSY,
    "user-quota": OWN_QUOTA,
    "deployment-quota": SHARED_QUOTA,
    "quota": SHARED_QUOTA,
}
NOT_SET_UP = frozenset({"live-off", "not-configured"})


def message(result, *, unavailable, not_set_up, manual):
    """Return the fixed message for a non-success gateway `result`.

    A refusal with a known cause gets its cause sentence followed by the
    feature's `manual` sentence; live calls off or no configuration gets the
    feature's `not_set_up` message; everything else gets `unavailable`.
    """
    if type(result) is gateway.Refused:
        if result.code in NOT_SET_UP:
            return not_set_up
        if result.code in CAUSES:
            return f"{CAUSES[result.code]} {manual}"
    return unavailable

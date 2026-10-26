"""The shared lookup of workspace-owned records (ACC-2.4)."""


def workspace_records(user, model):
    """Return `model`'s records in `user`'s workspace, and no other workspace's.

    Use it for every workspace record lookup: `get_object_or_404` on it gives
    another workspace's record the same 404 as a missing one, and as a form
    field's queryset it gives another workspace's ID the field's message.
    """
    return model._default_manager.filter(workspace_id=user.workspace_id)

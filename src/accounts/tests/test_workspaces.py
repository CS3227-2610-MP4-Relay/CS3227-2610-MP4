import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404

from accounts.models import User, Workspace
from accounts.workspaces import workspace_records

pytestmark = [pytest.mark.django_db, pytest.mark.ac("ACC-2.4")]


@pytest.fixture
def users():
    own = Workspace.objects.create(name="Demo workspace own00001")
    other = Workspace.objects.create(name="Demo workspace oth00001")
    return {
        name: User.objects.create_user(
            name, "Synthetic16Chars", workspace=workspace, role=role
        )
        for name, workspace, role in [
            ("coord-own00001", own, "coordinator"),
            ("tester1-own00001", own, "tester"),
            ("coord-oth00001", other, "coordinator"),
        ]
    }


def test_records_are_only_the_users_workspace(users):
    records = workspace_records(users["coord-own00001"], User)
    assert set(records.values_list("username", flat=True)) == {
        "coord-own00001",
        "tester1-own00001",
    }


def test_own_record_is_found(users):
    me = users["coord-own00001"]
    found = get_object_or_404(
        workspace_records(me, User), pk=users["tester1-own00001"].pk
    )
    assert found == users["tester1-own00001"]


def test_other_workspace_record_is_treated_as_missing(users):
    me = users["coord-own00001"]
    other_pk = users["coord-oth00001"].pk
    missing_pk = max(user.pk for user in users.values()) + 1000
    for pk in (other_pk, missing_pk):
        with pytest.raises(Http404):
            get_object_or_404(workspace_records(me, User), pk=pk)


def test_form_rejects_other_workspace_id_with_its_validation_message(users):
    me = users["coord-own00001"]
    field = forms.ModelChoiceField(queryset=workspace_records(me, User))
    assert field.clean(users["tester1-own00001"].pk) == users["tester1-own00001"]
    with pytest.raises(ValidationError) as refused:
        field.clean(users["coord-oth00001"].pk)
    assert refused.value.messages == [
        "Select a valid choice. That choice is not one of the available choices."
    ]

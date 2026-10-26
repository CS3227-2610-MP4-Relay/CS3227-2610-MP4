import re
import string
from unittest import mock

import pytest
from django.contrib.auth.hashers import check_password
from django.db import IntegrityError, transaction

from accounts import demo
from accounts.models import User, Workspace

ALPHABET = set(string.ascii_letters + string.digits)


def create(passwords=None):
    with transaction.atomic():
        return demo.create_demo_workspace(passwords or demo.generate_passwords())


def draws(*suffixes):
    return mock.patch.object(demo, "draw_suffix", side_effect=list(suffixes))


def test_generated_passwords_are_16_letters_and_digits_with_hashes():
    passwords = demo.generate_passwords()
    assert len(passwords) == 3
    assert len({password for password, _ in passwords}) == 3
    for password, hashed in passwords:
        assert len(password) == 16
        assert set(password) <= ALPHABET
        assert password not in hashed
        assert check_password(password, hashed)


def test_suffix_is_8_lowercase_letters_and_digits():
    for _ in range(20):
        assert re.fullmatch(r"[a-z0-9]{8}", demo.draw_suffix())


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.2")
def test_workspace_has_one_coordinator_and_two_testers():
    passwords = demo.generate_passwords()
    workspace, credentials = create(passwords)

    suffix = re.fullmatch(r"Demo workspace ([a-z0-9]{8})", workspace.name).group(1)
    assert [(c.role, c.username, c.password) for c in credentials] == [
        ("Test Coordinator", f"coord-{suffix}", passwords[0][0]),
        ("Beta Tester", f"tester1-{suffix}", passwords[1][0]),
        ("Beta Tester", f"tester2-{suffix}", passwords[2][0]),
    ]
    accounts = {user.username: user for user in workspace.accounts.all()}
    assert len(accounts) == 3
    for credential, role in zip(
        credentials, ["coordinator", "tester", "tester"], strict=True
    ):
        user = accounts[credential.username]
        assert user.role == role
        assert user.check_password(credential.password)


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.3")
def test_no_stored_field_holds_a_generated_password():
    _, credentials = create()
    stored = [
        str(value)
        for model in (Workspace, User)
        for row in model.objects.values_list()
        for value in row
    ]
    for credential in credentials:
        assert not any(credential.password in value for value in stored)


@pytest.mark.django_db
@pytest.mark.ac("ACC-2.4")
def test_two_workspaces_share_no_accounts():
    first, first_credentials = create()
    second, second_credentials = create()
    assert first.pk != second.pk
    first_names = {c.username for c in first_credentials}
    second_names = {c.username for c in second_credentials}
    assert not first_names & second_names
    assert set(first.accounts.values_list("username", flat=True)) == first_names
    assert set(second.accounts.values_list("username", flat=True)) == second_names


@pytest.mark.django_db
def test_taken_suffixes_are_redrawn_up_to_the_third_draw():
    taken_name = Workspace.objects.create(name="Demo workspace aaaa0001")
    User.objects.create_user(
        "tester2-bbbb0002", "Synthetic16Chars", workspace=taken_name, role="tester"
    )
    with draws("aaaa0001", "bbbb0002", "cccc0003", "dddd0004") as drawn:
        workspace, credentials = create()
    assert drawn.call_count == 3
    assert workspace.name == "Demo workspace cccc0003"
    assert credentials[0].username == "coord-cccc0003"


@pytest.mark.django_db
@pytest.mark.parametrize("taken", ["workspace", "username"])
def test_third_taken_suffix_fails_and_writes_nothing(taken):
    existing = Workspace.objects.create(name="Demo workspace other001")
    if taken == "workspace":
        Workspace.objects.create(name="Demo workspace aaaa0001")
    else:
        User.objects.create_user(
            "tester1-aaaa0001", "Synthetic16Chars", workspace=existing, role="tester"
        )
    before = (Workspace.objects.count(), User.objects.count())
    with (
        draws("aaaa0001", "aaaa0001", "aaaa0001", "bbbb0002") as drawn,
        pytest.raises(IntegrityError),
    ):
        create()
    assert drawn.call_count == 3
    assert (Workspace.objects.count(), User.objects.count()) == before

"""Generated credentials and the writes that create a demo workspace (ACC-2)."""

import secrets
import string
from typing import NamedTuple

from django.contrib.auth.hashers import make_password

from .models import User, Workspace

SUFFIX_ALPHABET = string.ascii_lowercase + string.digits
PASSWORD_ALPHABET = string.ascii_letters + string.digits
SUFFIX_DRAWS = 3
ACCOUNTS = (
    ("coord", User.Role.COORDINATOR),
    ("tester1", User.Role.TESTER),
    ("tester2", User.Role.TESTER),
)


class Credential(NamedTuple):
    """One account's role label, username and plain password, shown once."""

    role: str
    username: str
    password: str


def _random(alphabet, length):
    return "".join(secrets.choice(alphabet) for _ in range(length))


def draw_suffix():
    """Return a random 8-character suffix of lowercase letters and digits."""
    return _random(SUFFIX_ALPHABET, 8)


def generate_passwords():
    """Return a (password, hash) pair per demo account, hashed before any write."""
    passwords = [_random(PASSWORD_ALPHABET, 16) for _ in ACCOUNTS]
    return [(password, make_password(password)) for password in passwords]


def _usernames(suffix):
    return [f"{prefix}-{suffix}" for prefix, _ in ACCOUNTS]


def _is_taken(suffix):
    return (
        Workspace.objects.filter(name=f"Demo workspace {suffix}").exists()
        or User.objects.filter(username__in=_usernames(suffix)).exists()
    )


def _free_suffix():
    """Draw up to 3 suffixes; a last taken one fails on the unique constraints."""
    for _ in range(SUFFIX_DRAWS):
        suffix = draw_suffix()
        if not _is_taken(suffix):
            break
    return suffix


def create_demo_workspace(passwords):
    """Write a workspace and its accounts inside the caller's creation transaction.

    `passwords` comes from `generate_passwords`. Returns the workspace and its
    credentials in display order; a storage failure raises and the caller's
    transaction rolls everything back.
    """
    suffix = _free_suffix()
    workspace = Workspace.objects.create(name=f"Demo workspace {suffix}")
    credentials = []
    for username, (_, role), (password, hashed) in zip(
        _usernames(suffix), ACCOUNTS, passwords, strict=True
    ):
        User.objects.create(
            username=username, workspace=workspace, role=role, password=hashed
        )
        credentials.append(Credential(role.label, username, password))
    return workspace, credentials

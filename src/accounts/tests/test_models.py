import json

import pytest
from django.apps import apps
from django.conf import global_settings, settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from accounts.models import Workspace
from relay.settings import base
from relay.tests.test_configuration import probe

PASSWORD = "Synthetic16Chars"


def make_workspace(name="Demo workspace test0001"):
    return Workspace.objects.create(name=name)


def make_user(workspace, username="coord-test0001", role="coordinator"):
    return get_user_model().objects.create_user(
        username, PASSWORD, workspace=workspace, role=role
    )


def test_custom_user_model_has_no_admin_capability():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    fields = {field.name for field in get_user_model()._meta.get_fields()}
    assert {"username", "password", "workspace", "role", "last_login"} <= fields
    assert not fields & {
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
        "email",
    }
    assert not apps.is_installed("django.contrib.admin")


@pytest.mark.django_db
def test_create_user_stores_only_a_password_hash():
    user = make_user(make_workspace())
    user.refresh_from_db()
    assert user.password != PASSWORD
    assert PASSWORD not in user.password
    identify_hasher(user.password)
    assert user.check_password(PASSWORD)
    assert user.workspace.name == "Demo workspace test0001"
    assert user.role == "coordinator"


@pytest.mark.django_db
def test_username_is_unique_across_workspaces():
    make_user(make_workspace("Demo workspace aaaa0001"))
    with pytest.raises(IntegrityError), transaction.atomic():
        make_user(make_workspace("Demo workspace bbbb0002"))


@pytest.mark.django_db
def test_workspace_name_is_unique_and_creation_time_recorded():
    workspace = make_workspace()
    assert workspace.created_at is not None
    with pytest.raises(IntegrityError), transaction.atomic():
        make_workspace()


@pytest.mark.django_db
def test_account_requires_a_workspace():
    with pytest.raises(IntegrityError), transaction.atomic():
        get_user_model().objects.create(username="orphan-test0001", role="tester")


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["coordinator", "tester"])
def test_both_roles_are_accepted(role):
    assert make_user(make_workspace(), role=role).role == role


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["", "admin", "Coordinator"])
def test_database_rejects_other_roles(role):
    workspace = make_workspace()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_user(workspace, role=role)


@pytest.mark.django_db
def test_workspace_with_accounts_cannot_be_deleted():
    workspace = make_workspace()
    make_user(workspace)
    with pytest.raises(ProtectedError):
        workspace.delete()


@pytest.mark.django_db
def test_migrations_match_models():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


def test_sessions_and_cookies_use_shared_settings():
    assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.db"
    assert settings.SESSION_COOKIE_AGE == 8 * 60 * 60
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SECURE is True
    middleware = settings.MIDDLEWARE
    assert middleware.index(
        "django.contrib.sessions.middleware.SessionMiddleware"
    ) < middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware")
    assert "django.middleware.csrf.CsrfViewMiddleware" in middleware
    assert "django.contrib.messages.middleware.MessageMiddleware" in middleware
    assert (
        settings.MESSAGE_STORAGE
        == "django.contrib.messages.storage.session.SessionStorage"
    )


def test_local_settings_turn_secure_cookies_off():
    result = probe("relay.settings.local", DJANGO_SECRET_KEY="synthetic-local-key")
    assert result.returncode == 0, result.stderr
    cookies = json.loads(result.stdout)["cookies"]
    assert cookies == {"session_secure": False, "csrf_secure": False}


MD5 = "django.contrib.auth.hashers.MD5PasswordHasher"


def test_shared_and_local_settings_keep_the_default_hasher():
    shared = getattr(base, "PASSWORD_HASHERS", global_settings.PASSWORD_HASHERS)
    result = probe("relay.settings.local", DJANGO_SECRET_KEY="synthetic-local-key")
    assert result.returncode == 0, result.stderr
    local = json.loads(result.stdout)["hashers"]
    for hashers in (shared, local):
        assert hashers == global_settings.PASSWORD_HASHERS
        assert MD5 not in hashers

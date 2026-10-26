"""Workspaces and the role-based accounts that belong to them."""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class Workspace(models.Model):
    """An isolated group of accounts and the records they share."""

    name = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return the workspace name."""
        return self.name


class UserManager(BaseUserManager):
    """Create accounts with a hashed password, a workspace and a role."""

    def create_user(self, username, password, *, workspace, role):
        """Create and save an account, storing only the password hash."""
        user = self.model(username=username, workspace=workspace, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    """An account with one role in one workspace and no admin capability."""

    class Role(models.TextChoices):
        """The two product roles."""

        COORDINATOR = "coordinator", "Test Coordinator"
        TESTER = "tester", "Beta Tester"

    username = models.CharField(max_length=150, unique=True)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="accounts"
    )
    role = models.CharField(max_length=16, choices=Role.choices)

    USERNAME_FIELD = "username"
    objects = UserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["coordinator", "tester"]),
                name="accounts_user_role_valid",
            )
        ]


class LimitCounter(models.Model):
    """A fixed-window count of requests for one limit scope and key (ACC-3)."""

    class Scope(models.TextChoices):
        """Failed sign-ins and demo creations per address, and all demo creations."""

        SIGN_IN = "sign-in"
        DEMO = "demo"
        DEMO_TOTAL = "demo-total"

    scope = models.CharField(max_length=16, choices=Scope.choices)
    key = models.CharField(max_length=64)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "key"], name="accounts_limitcounter_scope_key"
            )
        ]

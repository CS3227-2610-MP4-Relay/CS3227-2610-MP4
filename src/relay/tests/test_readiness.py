from unittest.mock import MagicMock, patch

import pytest
from django.db import DatabaseError, InterfaceError, OperationalError, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext


def assert_response(response, status, body):
    assert response.status_code == status
    assert response.content == body
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response["Content-Length"] == ("6" if status == 200 else "12")
    assert {"no-store", "no-cache", "private", "max-age=0"} <= set(
        response["Cache-Control"].split(", ")
    )
    assert "Expires" in response


@pytest.mark.ac("PLT-1.15")
@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "head"])
def test_readiness_queries_runtime_database_without_application_data(client, method):
    with CaptureQueriesContext(connection) as queries:
        response = getattr(client, method)("/health/ready/?query=private-input")
    assert [query["sql"] for query in queries] == ["SELECT 1"]
    assert_response(response, 200, b"ready\n" if method == "get" else b"")
    assert not response.cookies


@pytest.mark.ac("PLT-1.15")
@pytest.mark.parametrize("method", ["get", "head"])
@pytest.mark.parametrize("phase", ["connect", "execute", "fetch"])
@pytest.mark.parametrize("error", [OperationalError, InterfaceError, DatabaseError])
def test_database_failures_are_generic_and_uncached(
    client, caplog, method, phase, error
):
    cursor = MagicMock()
    failure = error("synthetic-private-database-password")
    if phase != "connect":
        getattr(
            cursor, "execute" if phase == "execute" else "fetchone"
        ).side_effect = failure
    with patch.object(connection, "cursor") as open_cursor:
        if phase == "connect":
            open_cursor.side_effect = failure
        else:
            open_cursor.return_value.__enter__.return_value = cursor
        response = getattr(client, method)("/health/ready/")
    assert_response(response, 503, b"unavailable\n" if method == "get" else b"")
    assert "synthetic-private" not in caplog.text
    if phase != "connect":
        cursor.execute.assert_called_once_with("SELECT 1")


@pytest.mark.ac("PLT-1.15")
@pytest.mark.parametrize(
    "method", ["post", "put", "patch", "delete", "options", "trace"]
)
def test_readiness_rejects_writing_methods_before_database_access(method):
    with patch.object(connection, "cursor") as cursor:
        response = getattr(Client(enforce_csrf_checks=True), method)("/health/ready/")
    assert response.status_code == 405
    assert set(response["Allow"].split(", ")) == {"GET", "HEAD"}
    cursor.assert_not_called()

import pytest
from django.db import connection, transaction


@pytest.mark.ac("PLT-1.6")
@pytest.mark.django_db
def test_postgresql_synthetic_roundtrip():
    assert connection.vendor == "postgresql"
    assert connection.settings_dict["NAME"] == "test_relay_test"
    with connection.cursor() as cursor:
        cursor.execute("CREATE TEMPORARY TABLE relay_probe (value integer)")
        with transaction.atomic():
            cursor.execute("INSERT INTO relay_probe (value) VALUES (%s)", [42])
            cursor.execute("SELECT value FROM relay_probe")
            assert cursor.fetchone() == (42,)
            transaction.set_rollback(True)
        cursor.execute("SELECT count(*) FROM relay_probe")
        assert cursor.fetchone() == (0,)

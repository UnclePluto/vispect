import pytest

@pytest.fixture(autouse=True)
def runtime_database(django_db_blocker):
    with django_db_blocker.unblock():
        yield

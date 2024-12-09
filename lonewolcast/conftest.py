import pytest
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }

@pytest.fixture(autouse=True)
def mock_firebase():
    """Mock Firebase pour les tests."""
    try:
        app = firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": "test",
            "private_key_id": "test",
            "private_key": "test",
            "client_email": "test",
            "client_id": "test",
            "auth_uri": "test",
            "token_uri": "test",
            "auth_provider_x509_cert_url": "test",
            "client_x509_cert_url": "test"
        })
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://test.firebaseio.com'
        })

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()
from .settings import *

# Base de données de test
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}

# Désactiver le CSRF pour les tests
REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
}

# Configuration Firebase de test
FIREBASE_CONFIG = {
    'databaseURL': 'https://test.firebaseio.com'
}

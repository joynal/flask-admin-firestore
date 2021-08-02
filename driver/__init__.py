# flake8: noqa
try:
    import firebase_admin
except ImportError:
    raise Exception('Please install firebase_admin in order to use firestore backend')

from .view import ModelView
from .form import EmbeddedForm

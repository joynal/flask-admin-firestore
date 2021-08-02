from firebase_admin import ValidationError
from wtforms.validators import ValidationError as wtfValidationError
from flask_admin._compat import itervalues, as_unicode


def format_error(error):
    if isinstance(error, ValidationError):
        return as_unicode(error)

    if isinstance(error, wtfValidationError):
        return '. '.join(itervalues(error.to_dict()))

    return as_unicode(error)

from flask_admin.model.fields import InlineFormField


def is_empty(file_object):
    file_object.seek(0)
    first_char = file_object.read(1)
    file_object.seek(0)
    return not bool(first_char)


class ModelFormField(InlineFormField):
    """
        Customized ModelFormField for MongoEngine EmbeddedDocuments.
    """
    def __init__(self, model, view, form_class, form_opts=None, **kwargs):
        super(ModelFormField, self).__init__(form_class, **kwargs)

        self.model = model
        if isinstance(self.model, str):
            # TODO: replace get_document
            self.model = get_document(self.model)

        self.view = view
        self.form_opts = form_opts

    def populate_obj(self, obj, name):
        candidate = getattr(obj, name, None)
        is_created = candidate is None
        if is_created:
            candidate = self.model()
            setattr(obj, name, candidate)

        self.form.populate_obj(candidate)

        self.view._on_model_change(self.form, candidate, is_created)


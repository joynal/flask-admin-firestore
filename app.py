from flask import Flask
import flask_admin as admin
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from wtforms import form, fields

from flask_admin.form import Select2Widget
from flask_admin.model.fields import InlineFormField, InlineFieldList

# Create application
app = Flask(__name__)

# Create dummy secrey key so we can use sessions
app.config['SECRET_KEY'] = '123456790'

cred = credentials.Certificate('/Users/joynal/.gcloud/kamata-dev.json')
firebase_admin.initialize_app(cred, {
  'projectId': 'kamata-dev',
})

db = firestore.client()


class InnerForm(form.Form):
    name = fields.StringField('Name')
    test = fields.StringField('Test')


class UserForm(form.Form):
    name = fields.StringField('Name')
    email = fields.StringField('Email')
    password = fields.StringField('Password')

    # Inner form
    inner = InlineFormField(InnerForm)

    # Form list
    form_list = InlineFieldList(InlineFormField(InnerForm))


class AgentForm(form.Form):
    name = fields.StringField('Name')
    user_id = fields.SelectField('User', widget=Select2Widget())
    text = fields.StringField('Text')

    testie = fields.BooleanField('Test')


class AgentView(admin.BaseView):
    column_list = ('name', 'user_name', 'text')
    column_sortable_list = ('name', 'text')

    column_searchable_list = ('name', 'text')

    form = AgentForm

    def get_list(self, *args, **kwargs):
        data = super(AgentView, self).get_list(*args, **kwargs)

        # TODO: fix me
        count = 10000
        coll = (
            db.collection("deo")
            .document("entities")
            .collection("agents")
            .limit(10)
            .offset(0)
            .order_by("created_at", "DESCENDING")
            .get()
        )

        data = [item.to_dict() for item in coll]

        return count, data

    # Contribute list of user choices to the forms
    def _feed_user_choices(self, form):
        users = db.user.find(fields=('name',))
        form.user_id.choices = [(str(x['_id']), x['name']) for x in users]
        return form

    def create_form(self):
        form = super(AgentView, self).create_form()
        return self._feed_user_choices(form)

    def edit_form(self, obj):
        form = super(AgentView, self).edit_form(obj)
        return self._feed_user_choices(form)

    # Correct user_id reference before saving
    def on_model_change(self, form, model):
        user_id = model.get('user_id')
        # model['user_id'] = ObjectId(user_id)

        return model


# Flask views
@app.route('/')
def index():
    return '<a href="/admin/">Click me to get to Admin!</a>'


if __name__ == '__main__':
    # Create admin
    admin = admin.Admin(app, name='Firestore')

    # Add views
    admin.add_view(AgentView(name="Agents", category='Agents'))

    # Start app
    app.run(debug=True)

import logging
from flask import Flask
import flask_admin as admin
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as firestore_client

from wtforms import form, fields

from firestore.view import ModelView

logging.basicConfig(level=logging.DEBUG)

# Create application
app = Flask(__name__)

# Create dummy secret key so we can use sessions
app.config["SECRET_KEY"] = "123456790"

cred = credentials.Certificate("/Users/joynal/.gcloud/kamata-dev.json")
firebase_admin.initialize_app(
    cred,
    {
        "projectId": "kamata-dev",
    },
)

db = firestore_client.client()

class AgentForm(form.Form):
    first_name = fields.StringField("First Name")
    last_name = fields.StringField("Last Name")
    email = fields.StringField("Email")


class AgentView(ModelView):
    #column_list = ("created_at", "id", "first_name", "last_name", "email")

    form = AgentForm

    # def get_list(self, *args, **kwargs):
    #     data = super(AgentView, self).get_list(*args, **kwargs)

    #     # TODO: fix me
    #     count = 10000
    #     coll = (
    #         self.db.limit(10)
    #         .offset(0)
    #         .order_by("created_at", "DESCENDING")
    #         .get()
    #     )

    #     data = []

    #     for item in coll:
    #         item_parsed = item.to_dict();
    #         item_parsed['pk'] = item_parsed['id']

    #         print(item_parsed)

    #         data.append(item_parsed)

    #     # data = [item.to_dict() for item in coll]

    #     return count, data

    # Contribute list of user choices to the forms
    def _feed_user_choices(self, form):
        # users = db.user.find(fields=("first_name",))
        # form.user_id.choices = [(str(x["id"]), x["first_name"]) for x in users]
        return form

    def create_form(self):
        form = super(AgentView, self).create_form()
        return self._feed_user_choices(form)

    def edit_form(self, obj):
        form = super(AgentView, self).edit_form(obj)
        return self._feed_user_choices(form)

    # Correct user_id reference before saving
    def on_model_change(self, form, model):
        user_id = model.get("user_id")
        # model['user_id'] = ObjectId(user_id)

        return model

# Flask views
@app.route("/")
def index():
    return '<a href="/admin/">Click me to get to Admin!</a>'

env = "demo"

# Create admin
admin = admin.Admin(app, name=env)

# Add views
collections = db.collection(env).document("entities").collections()

for collection in collections:
    admin.add_view(AgentView(coll=collection, name=collection.id))


if __name__ == "__main__":
    # Start app
    app.run(debug=True)

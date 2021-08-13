import logging


from typing import List, Tuple, Dict, Iterable, Any, Optional
import uuid
from google.cloud import firestore

from flask import flash

from flask_admin._compat import string_types
from flask_admin.babel import gettext, ngettext, lazy_gettext
from flask_admin.model import BaseModelView
from flask_admin.actions import action
from flask_admin.helpers import get_form_data
from flask_admin.model import filters

from .filters import BaseFirebaseFilter
from .tools import parse_like_term

# Set up logger
log = logging.getLogger("flask-admin.firestore")

Query = List[Tuple[str, str, str]]

class ModelView(BaseModelView):
    """
        MongoEngine model scaffolding.
    """

    column_filters = None
    """
        Collection of the column filters.
        Should contain instances of
        :class:`flask_admin.contrib.pymongo.filters.BasePyMongoFilter` classes.
        Filters will be grouped by name when displayed in the drop-down.
        For example::
            from flask_admin.contrib.pymongo.filters import BooleanEqualFilter
            class MyModelView(BaseModelView):
                column_filters = (BooleanEqualFilter(column=User.name, name='Name'),)
        or::
            from flask_admin.contrib.pymongo.filters import BasePyMongoFilter
            class FilterLastNameBrown(BasePyMongoFilter):
                def apply(self, query, value):
                    if value == '1':
                        return query.filter(self.column == "Brown")
                    else:
                        return query.filter(self.column != "Brown")
                def operation(self):
                    return 'is Brown'
            class MyModelView(BaseModelView):
                column_filters = [
                    FilterLastNameBrown(
                        column=User.last_name, name='Last Name',
                        options=(('1', 'Yes'), ('0', 'No'))
                    )
                ]
    """

    def __init__(self, coll: firestore.CollectionReference,
                 name=None, category=None, endpoint=None, url=None,
                 menu_class_name=None, menu_icon_type=None, menu_icon_value=None, include_raw: bool=False):
        """
            Constructor
            :param coll:
                MongoDB collection object
            :param name:
                Display name
            :param category:
                Display category
            :param endpoint:
                Endpoint
            :param url:
                Custom URL
            :param menu_class_name:
                Optional class name for the menu item.
            :param menu_icon_type:
                Optional icon. Possible icon types:
                 - `flask_admin.consts.ICON_TYPE_GLYPH` - Bootstrap glyph icon
                 - `flask_admin.consts.ICON_TYPE_FONT_AWESOME` - Font Awesome icon
                 - `flask_admin.consts.ICON_TYPE_IMAGE` - Image relative to Flask static directory
                 - `flask_admin.consts.ICON_TYPE_IMAGE_URL` - Image with full URL
            :param menu_icon_value:
                Icon glyph name or URL, depending on `menu_icon_type` setting
        """
        self._search_fields = []

        self.coll = coll

        if name is None:
            name = self._prettify_name(coll.id)

        if endpoint is None:
            endpoint = ('%sview' % name).lower()

        self.can_create = False
        self.can_edit = False
        self.can_delete = False
        self.include_raw = False

        self.action_disallowed_list = ['create', 'delete', 'edit']
        
        super(ModelView, self).__init__(None, name, category, endpoint, url,
                                        menu_class_name=menu_class_name,
                                        menu_icon_type=menu_icon_type,
                                        menu_icon_value=menu_icon_value)


    def scaffold_pk(self):
        return 'id'

    def get_pk_value(self, model: firestore.DocumentSnapshot):
        """
            Return primary key value from the model instance
            :param model:
                Model instance
        """
        return model.get('id')

    def scaffold_list_columns(self):
        """
            Scaffold list columns
        """
        cols = ["id"]

        docs: List[firestore.DocumentSnapshot] = list(self.coll.limit(1).get())
        if docs:
            doc: Optional[Dict[str, Any]] = docs[0].to_dict()
            if doc:
                doc.pop("id", None)
                cols.extend(sorted(doc.keys()))
        
        
        if self.include_raw:
            cols.append("raw")
        return cols

    def scaffold_sortable_columns(self):
        """
            Return sortable columns dictionary (name, field)
        """
        return self.scaffold_list_columns()

    def init_search(self):
        """
            Init search
        """
        if self.column_searchable_list:
            for p in self.column_searchable_list:
                if not isinstance(p, string_types):
                    raise ValueError('Expected string')

                # TODO: Validation?

                self._search_fields.append(p)

        return bool(self._search_fields)

    def scaffold_filters(self, attr):
        """
            Return filter object(s) for the field
            :param name:
                Either field name or field instance
        """
        raise NotImplementedError()

    def is_valid_filter(self, filter):
        """
            Validate if it is valid MongoEngine filter
            :param filter:
                Filter object
        """
        return isinstance(filter, BaseFirebaseFilter)

    def scaffold_form(self):
        raise NotImplementedError()

    def _get_field_value(self, model: firestore.DocumentSnapshot, name: str):
        """
            Get unformatted field value from the model
        """
        if name == "raw":
            return model.to_dict()

        return model.get(name)

    def _search(self, query: Query, search_term: str) -> Query:
        values = search_term.split(' ')

        queries = query

        # Construct inner query
        for value in values:
            if not value:
                continue

            regex = parse_like_term(value)

            stmt = []
            for field in self._search_fields:
                stmt.append((field, "==", regex))

            if stmt:
                queries.append(stmt[0])

        return queries

    def get_list(self, page, sort_column, sort_desc, search, filters: Dict[str, filters.BaseFilter],
                 execute=True, page_size=None):
        """
            Get list of objects from Firestore
            :param page:
                Page number
            :param sort_column:
                Sort column
            :param sort_desc:
                Sort descending
            :param search:
                Search criteria
            :param filters:
                List of applied fiters
            :param execute:
                Run query immediately or not
            :param page_size:
                Number of results. Defaults to ModelView's page_size. Can be
                overridden to change the page_size limit. Removing the page_size
                limit requires setting page_size to 0 or False.
        """
        query:Query  = []

        # Filters
        if self._filters:
            data = []

            for flt, flt_name, value in filters:
                f = self._filters[flt]
                data = f.apply(data, f.clean(value))

            if data:
                if len(data) == 1:
                    query = data[0]

        # Search
        if self._search_supported and search:
            query = self._search(query, search)

        # Pagination
        if page_size is None:
            page_size = self.page_size

        skip = 0

        if page and page_size:
            skip = page * page_size

        # Construct the query
        query_ref = firestore.Query(parent=self.coll, limit=page_size, offset=skip)

        # Sorting
        sort_by = ()

        if sort_column:
            query_ref = query_ref.order_by(sort_column, firestore.Query.DESCENDING if sort_desc else firestore.Query.ASCENDING)
        else:
            order = self._get_default_order()

            if order:
                for (col, desc) in order:
                    query_ref = query_ref.order_by(col, firestore.Query.DESCENDING if desc else firestore.Query.ASCENDING)

        for query_term in query:
            query_ref = query_ref.where(*query_term)

        results = query_ref.stream()

        log.info(results)

        if execute:
            results = list(results)

        return None, results

    def _get_valid_id(self, id):
        try:
            return uuid.UUID(id)
        except ValueError:
            return id

    def get_one(self, id):
        """
            Return single model instance by ID
            :param id:
                Model ID
        """
        return self.coll.document(str(self._get_valid_id(id)))

    def edit_form(self, obj):
        """
            Create edit form from the MongoDB document
        """
        return self._edit_form_class(get_form_data(), **obj.get().to_dict())

    # def create_model(self, form):
    #     """
    #         Create model helper
    #         :param form:
    #             Form instance
    #     """
    #     try:
    #         model = form.data
    #         self._on_model_change(form, model, True)
    #         self.coll.insert(model)
    #     except Exception as ex:
    #         flash(gettext('Failed to create record. %(error)s', error=str(ex)),
    #               'error')
    #         log.exception('Failed to create record.')
    #         return False
    #     else:
    #         self.after_model_change(form, model, True)

    #     return model

    # def update_model(self, form, model):
    #     """
    #         Update model helper
    #         :param form:
    #             Form instance
    #         :param model:
    #             Model instance to update
    #     """
    #     try:
    #         model.update(form.data)
    #         self._on_model_change(form, model, False)

    #         pk = self.get_pk_value(model)
    #         self.coll.update({'_id': pk}, model)
    #     except Exception as ex:
    #         flash(gettext('Failed to update record. %(error)s', error=str(ex)),
    #               'error')
    #         log.exception('Failed to update record.')
    #         return False
    #     else:
    #         self.after_model_change(form, model, False)

    #     return True

    # def delete_model(self, model):
    #     """
    #         Delete model helper
    #         :param model:
    #             Model instance
    #     """
    #     try:
    #         pk = self.get_pk_value(model)

    #         if not pk:
    #             raise ValueError('Document does not have _id')

    #         self.on_model_delete(model)
    #         self.coll.remove({'_id': pk})
    #     except Exception as ex:
    #         flash(gettext('Failed to delete record. %(error)s', error=str(ex)),
    #               'error')
    #         log.exception('Failed to delete record.')
    #         return False
    #     else:
    #         self.after_model_delete(model)

    #     return True

    # Default model actions
    def is_action_allowed(self, name):
        # Check delete action permission
        return False

        if name == 'delete' and not self.can_delete:
            return False

        return super(ModelView, self).is_action_allowed(name)

    @action('delete',
            lazy_gettext('Delete'),
            lazy_gettext('Are you sure you want to delete selected records?'))
    def action_delete(self, ids):
        try:
            count = 0

            # TODO: Optimize me
            for pk in ids:
                if self.delete_model(self.get_one(pk)):
                    count += 1

            flash(ngettext('Record was successfully deleted.',
                           '%(count)s records were successfully deleted.',
                           count,
                           count=count), 'success')
        except Exception as ex:
            flash(gettext('Failed to delete records. %(error)s', error=str(ex)), 'error')
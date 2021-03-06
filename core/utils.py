# -*- coding: utf-8 -*-
import re
import types
import uuid

from bson import ObjectId
from datetime import datetime
from flask import current_app, render_template, json, Blueprint
from importlib import import_module
from time import time
from os.path import abspath, dirname, join
from speaklater import _LazyString
from unidecode import unidecode

from werkzeug.datastructures import Headers
from werkzeug.utils import import_string, cached_property


class LazyView(object):

    def __init__(self, import_name, endpoint=None):
        self.__module__, self.__name__ = import_name.rsplit('.', 1)
        self.import_name = import_name
        self.endpoint = endpoint

    def __call__(self, *args, **kwargs):
        return self.view(*args, **kwargs)

    @cached_property
    def view(self):
        return import_string(self.import_name)


class LazyResource(LazyView):

    @cached_property
    def view(self):
        resource_cls = import_string(self.import_name)
        return resource_cls.as_view(self.endpoint)


def add_api_rule(bp, endpoint, pk_def, import_name):
    resource = LazyResource(import_name, endpoint)
    collection_url = "/{}/".format(endpoint)
    # collection endpoint
    collection_methods = ['GET', 'PUT', 'POST']
    item_methods = ['GET', 'PUT', 'DELETE']

    pk = pk_def.keys()[0]
    pk_type = pk_def[pk] and pk_def[pk].__name__ or None

    if pk_type is None:
        item_url = "{}<{}>".format(collection_url, pk)
    else:
        item_url = "{}<{}:{}>".format(collection_url, pk_type, pk)

    bp.add_url_rule(collection_url, view_func=resource, endpoint=endpoint,
                    methods=collection_methods)
    bp.add_url_rule(item_url, view_func=resource, endpoint=endpoint,
                    methods=item_methods)


def add_url_rule(blueprint, namespace, path, method, **kwargs):
    method_path = ".".join([namespace, method])
    return blueprint.add_url_rule(path, view_func=LazyView(method_path),
                                  **kwargs)

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
lazy_cascade = {'lazy': 'dynamic', 'cascade': 'all'}


class CustomEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.ctime()
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, _LazyString):
            return unicode(obj)
        if hasattr(obj, 'as_dict'):
            return obj.as_dict()
        return super(CustomEncoder, self).default(obj)


def json_dumps(data):
    try:
        return json.dumps(data, cls=CustomEncoder)
    except ValueError as e:
        current_app.logger.debug("%s: %s", e.message, data)
        raise e


def jsonify_status_code(data=None, status=200, mimetype='application/json'):
    data = data or {}

    return current_app.response_class(json_dumps(data),
                                      status=status, mimetype=mimetype)


def slugify(text, separator='-', prefix=True):
    text = unidecode(text)
    text = re.sub('[^\w\s]', '', text)
    text = re.sub('[^\w]', separator, text)
    if prefix:
        hsh = uuid.uuid4().hex[:4]
        text = '%s%s%s' % (text, separator, hsh)
    return text.lower()


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """ Returns a bytestring version of 's', encoded as specified in
        'encoding'. If strings_only is True, don't convert (some)
        non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s


def resolve_class(class_path):
    """ helper method for importing class by class path string repesentation
    """
    module_name, class_name = class_path.rsplit('.', 1)
    return getattr(import_module(module_name), class_name)


def rules(language):
    """ helper method for getting plural form rules from the text file
    """
    rule_file = join(dirname(abspath(__file__)), 'rules.%s') % language
    for line in file(rule_file):
        pattern, search, replace = line.split()
        yield lambda word: re.search(pattern, word) and \
                re.sub(search, replace, word)


def plural_name(noun, language='en'):
    """ pluralize a noun for the selected language
    """
    for applyRule in rules(language):
        result = applyRule(noun)
        if result:
            return result


def underscorize(name):
    """ Converts CamelCase notation to the camel_case
    """
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


plural_underscored = lambda s: plural_name(underscorize(s))


def send_email(subject, recipient, template, attachments=None, **context):
    """ Send an email via the Flask-Mail extension.

    :param subject: Email subject
    :param recipient: Email recipient
    :param template: The name of the email template
    :param context: The context to render the template with
    """
    from background.tasks import send_message_from_queue
    from .documents import StoredMail
    ctx = ('email', template)
    message = StoredMail(
        subject=subject,
        # text_body=render_template('{0}/{1}.txt'.format(*ctx), **context),
        html_body=render_template('{0}/{1}.html'.format(*ctx), **context),
    )
    message.recipients.extend(isinstance(recipient, basestring) and [recipient] or recipient)
    attachments and message.attachments.extend(attachments)
    message.save()
    # Pass message to celery
    send_message_from_queue.delay(message.id)


class AttrDict(dict):
    """
    """
    _protected_fields = ['_protected_fields']

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self._protected_fields.extend(self.__dict__.keys())

    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            return self.__getattribute__(item)

    def __setattr__(self, key, value):
        if key not in self.__getattribute__('_protected_fields'):
            self[key] = value

        else:
            dict.__setattr__(self, key, value)


def x_accel_gridfs(file_field):
    headers = Headers()
    headers['X-Accel-Redirect'] = "/img/{}".format(file_field.grid_id)
    mimetype = file_field.contentType

    rv = current_app.response_class(None, mimetype=mimetype, headers=headers,
                                    direct_passthrough=True)
    cache_timeout = current_app.config['SEND_FILE_MAX_AGE_DEFAULT']

    rv.cache_control.max_age = cache_timeout
    rv.cache_control.public = True
    rv.expires = int(time() + cache_timeout)
    rv.last_modified = file_field.uploadDate

    rv.set_etag('flamaster-{}-{}-{}'.format(
        file_field.uploadDate,
        file_field.length,
        file_field.grid_id
    ))

    return rv


class ResourceBlueprint(Blueprint):

    def add_resource(self, endpoint, pk_def, class_name):
        if class_name.startswith('.'):
            import_path = "{}.api{}".format(self.import_name, class_name)
        else:
            import_path = class_name
        resource = LazyResource(import_path, endpoint)
        collection_url = "/{}/".format(endpoint)

        # collection endpoint
        collection_methods = ['GET', 'PUT', 'POST']
        item_methods = ['GET', 'PUT', 'DELETE']

        pk = pk_def.keys()[0]
        pk_type = pk_def[pk] and pk_def[pk].__name__ or None

        if pk_type is None:
            item_url = "{}<{}>".format(collection_url, pk)
        else:
            item_url = "{}<{}:{}>".format(collection_url, pk_type, pk)

        self.add_url_rule(collection_url, view_func=resource, endpoint=endpoint, methods=collection_methods)
        self.add_url_rule(item_url, view_func=resource, endpoint=endpoint, methods=item_methods)

    def add_view(self, path, method, **kwargs):
        import_path = "{}.views.{}".format(self.import_name, method)
        return self.add_url_rule(path, view_func=LazyView(import_path), **kwargs)
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import sqlamp
from datetime import datetime

from flask.ext.sqlalchemy import orm

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

#  import class_mapper, object_mapper
from flamaster.extensions import db
from .utils import slugify, plural_underscored


def raise_value(text):
    raise ValueError(text)


class BaseMixin(object):
    """ Base mixin
    """
    __table_args__ = {'extend_existing': True}

    @declared_attr
    def __tablename__(cls):
        """ We want our app to be more English for pluralization cases
        """
        return plural_underscored(cls.__name__)

    def as_dict(self, include=None, exclude=None):
        """ method for building dictionary for model value-properties filled
            with data from mapped storage backend
        """
        column_properties = [p.key for p in self.__mapper__.iterate_properties
                                if isinstance(p, orm.ColumnProperty)]
        fields = [field.strip('_') for field in column_properties]

        exportable_fields = (include or []) + fields
        exportable_fields = set(exportable_fields) - set(exclude or [])
        # convert undescored fields:

        result = dict()
        for field in exportable_fields:
            value = getattr(self, field)

            if hasattr(value, '__call__'):
                value = value()
            result[field] = value

        return result


class CRUDMixin(BaseMixin):
    """ Basic CRUD mixin
    """

    @declared_attr
    def id(cls):
        return db.Column(db.Integer, primary_key=True)

    @declared_attr
    def created_at(cls):
        return db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get(cls, id):
        return cls.query.get(id)

    @classmethod
    def create(cls, commit=True, **kwargs):
        return cls(**kwargs).save(commit)

    def update(self, commit=True, **kwargs):
        return self._setattrs(**kwargs).save(commit)

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        db.session.delete(self)
        if commit:
            db.session.commit()

    def _setattrs(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k.startswith('_'):
                raise ValueError('Underscored values are not allowed')
            setattr(self, k, v)
        return self


class SlugMixin(CRUDMixin):
    """Basic mixin for models with slug and name
    """
    @declared_attr
    def name(cls):
        return db.Column(db.Unicode(512), nullable=False)

    @declared_attr
    def _slug(cls):
        return db.Column(db.String(128), nullable=False, unique=True)

    @hybrid_property
    def slug(self):
        return self._slug

    @slug.setter
    def slug(self, name):
        self._slug = slugify(name)

    def save(self, commit=True):
        self.slug = self.name
        return super(SlugMixin, self).save(commit)

    @classmethod
    def get_by_slug(cls, slug):
        return cls.query.filter_by(slug=slug).first()

    def __repr__(self):
        return "<%s:%s>" % (self.__class__.__name__,
                            self.id)


class NodeMetaClass(type(db.Model), sqlamp.DeclarativeMeta):
    """this hack exists for the safe connection tree with
    the flask alchemy session initialization
    """

    def __init__(self, name, bases, dct):
        bind_key = dct.pop('__bind_key__', None)
        sqlamp.DeclarativeMeta.__init__(self, name, bases, dct)
        if bind_key is not None:
            self.__table__.info['bind_key'] = bind_key


class TreeNode(CRUDMixin):
    """ Mixin for self-Referential relationships.
        The final model should be with NodeMetaClass and
        a special class variable ``__mp_manager__ = 'mp'`` should exist
        which will be used as `MPManager` descriptor property to
        support Materialized Path functionality.
        Check <http://sqlamp.angri.ru> for the detailed usage documentation
    """

    @declared_attr
    def parent_id(cls):
        table_name = plural_underscored(cls.__name__)
        return db.Column(db.Integer,
                         db.ForeignKey("{}.id".format(table_name),
                                       ondelete="CASCADE",
                                       onupdate="CASCADE")
                         )

    @declared_attr
    def parent(cls):
        # remote side should point to the class attribute
        return db.relationship(cls.__name__, backref='children',
                               remote_side="{}.id".format(cls.__name__))

    def delete(self, commit=True):
        """
        Overrided method to delete a whole tree/subtree of the node
        """
        instance = self.query.get(self.id)
        self.__class__.mp.delete_subtree(db.session, instance.id)
        if commit:
            db.session.commit()

    def update(self, **kwargs):
        """ Overrided update method from CRUDMixin
        """
        instance = self._setattrs(**kwargs).save(commit=True)
        # rebuild Materialized Path tree structure
        self.__class__.mp.drop_indices(db.session)
        self.__class__.mp.rebuild_all_trees(db.session)
        self.__class__.mp.create_indices(db.session)

        return self.query.get(instance.id)

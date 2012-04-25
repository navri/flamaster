from flamaster.core.utils import check_permission
from flask import g#url_for
from flamaster.app import db, app
from conftest import create_user, request_context, login#, url_client#, valid_user,
from flamaster.account.models import Role, User, Permissions


@app.teardown_request
def teardown_request(exception=None):
    print dir(g)


def setup_module(module):
    db.create_all()


@request_context
def test_save_in_user_check_permission():
    assert Role.query.all() == []
    create_user()
    role = Role.query.filter_by(name='user')
    assert role.count() == 1
    with app.test_client() as c:
        assert getattr(g, 'user', False) == False
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        user.set_password('test').save()
        login(c, 'test@example.com', 'test')
        assert getattr(g, 'user', False) == None
        Permissions.create(name='test_permissions1')
        Role.get(user.role_id).permissions.append(
            Permissions('test_permissions_in_role2'))
        assert check_permission('test_permissions1') == False
        assert check_permission('test_permissions_in_role2') == True


def teardown_module(module):
    db.drop_all()

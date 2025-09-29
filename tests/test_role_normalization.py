import pytest
from journal import create_app, db
from journal.models import User
from sqlalchemy import text


@pytest.fixture
def app():
    config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    }
    app = create_app(config=config)
    return app


def test_role_normalization_on_insert(app):
    with app.app_context():
        # ensure tables exist
        db.create_all()

        # create a user with uppercase role assigned (simulate bad input)
        u = User(username='normtest', email='norm@example.com', password='pw', role='ADMIN')
        db.session.add(u)
        db.session.commit()

        # read raw stored value from DB to ensure it's normalized to lowercase
        stored = db.session.execute(text("SELECT role FROM user WHERE id = :id"), {'id': u.id}).scalar()
        assert stored == 'admin'

        # update role via ORM to REVIEWER and ensure stored lowercase
        u.role = 'REVIEWER'
        db.session.commit()
        stored2 = db.session.execute(text("SELECT role FROM user WHERE id = :id"), {'id': u.id}).scalar()
        assert stored2 == 'reviewer'

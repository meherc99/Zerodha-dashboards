"""
Tests for TransactionCategory model
"""
import pytest
from datetime import datetime
from app import create_app, db
from app.models.transaction_category import TransactionCategory


@pytest.fixture
def app():
    """Create and configure test app"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


def test_category_creation(app):
    """Test creating a category with required fields"""
    with app.app_context():
        category = TransactionCategory(
            name='Income',
            icon='💰',
            color='#10b981'
        )

        db.session.add(category)
        db.session.commit()

        assert category.id is not None
        assert category.name == 'Income'
        assert category.icon == '💰'
        assert category.color == '#10b981'
        assert category.parent_category_id is None
        assert category.keywords == []
        assert category.is_system is True
        assert category.created_at is not None
        assert isinstance(category.created_at, datetime)


def test_category_with_keywords(app):
    """Test creating a category with keywords"""
    with app.app_context():
        category = TransactionCategory(
            name='Groceries',
            icon='🛒',
            color='#10b981',
            keywords=['grocery', 'supermarket', 'bigbasket', 'grofers', 'blinkit']
        )

        db.session.add(category)
        db.session.commit()

        assert category.keywords == ['grocery', 'supermarket', 'bigbasket', 'grofers', 'blinkit']
        assert len(category.keywords) == 5


def test_unique_name_constraint(app):
    """Test category name uniqueness is enforced"""
    with app.app_context():
        category1 = TransactionCategory(
            name='Dining',
            icon='🍽️',
            color='#ef4444'
        )
        db.session.add(category1)
        db.session.commit()

        # Attempting to create another category with same name should fail
        category2 = TransactionCategory(
            name='Dining',
            icon='🍔',
            color='#000000'
        )
        db.session.add(category2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db.session.commit()


def test_hierarchical_categories_parent_child(app):
    """Test creating parent-child category relationships"""
    with app.app_context():
        # Create parent category
        parent = TransactionCategory(
            name='Shopping',
            icon='🛍️',
            color='#ec4899'
        )
        db.session.add(parent)
        db.session.commit()

        # Create child categories
        clothing = TransactionCategory(
            name='Clothing',
            icon='👕',
            color='#ec4899',
            parent_category_id=parent.id
        )
        electronics = TransactionCategory(
            name='Electronics',
            icon='📱',
            color='#ec4899',
            parent_category_id=parent.id
        )
        db.session.add_all([clothing, electronics])
        db.session.commit()

        # Verify relationships
        assert clothing.parent_category_id == parent.id
        assert electronics.parent_category_id == parent.id
        assert clothing.parent == parent
        assert electronics.parent == parent
        assert len(parent.children) == 2
        assert clothing in parent.children
        assert electronics in parent.children


def test_category_without_parent(app):
    """Test top-level category without parent"""
    with app.app_context():
        category = TransactionCategory(
            name='Utilities',
            icon='⚡',
            color='#f59e0b'
        )
        db.session.add(category)
        db.session.commit()

        assert category.parent_category_id is None
        assert category.parent is None
        assert len(category.children) == 0


def test_system_vs_user_category(app):
    """Test is_system flag for system vs user-created categories"""
    with app.app_context():
        system_category = TransactionCategory(
            name='Income',
            icon='💰',
            color='#10b981',
            is_system=True
        )
        user_category = TransactionCategory(
            name='Custom Category',
            icon='📝',
            color='#000000',
            is_system=False
        )

        db.session.add_all([system_category, user_category])
        db.session.commit()

        assert system_category.is_system is True
        assert user_category.is_system is False


def test_category_to_dict(app):
    """Test to_dict() method returns correct dictionary"""
    with app.app_context():
        category = TransactionCategory(
            name='Healthcare',
            icon='🏥',
            color='#ef4444',
            keywords=['doctor', 'hospital', 'pharmacy', 'medicine']
        )
        db.session.add(category)
        db.session.commit()

        category_dict = category.to_dict()

        assert category_dict['id'] == category.id
        assert category_dict['name'] == 'Healthcare'
        assert category_dict['icon'] == '🏥'
        assert category_dict['color'] == '#ef4444'
        assert category_dict['parent_category_id'] is None
        assert category_dict['keywords'] == ['doctor', 'hospital', 'pharmacy', 'medicine']
        assert category_dict['is_system'] is True
        assert 'created_at' in category_dict
        assert isinstance(category_dict['created_at'], str)  # Should be ISO format


def test_category_to_dict_with_parent(app):
    """Test to_dict() includes parent_category_id when present"""
    with app.app_context():
        parent = TransactionCategory(
            name='Shopping',
            icon='🛍️',
            color='#ec4899'
        )
        db.session.add(parent)
        db.session.commit()

        child = TransactionCategory(
            name='Clothing',
            icon='👕',
            color='#ec4899',
            parent_category_id=parent.id
        )
        db.session.add(child)
        db.session.commit()

        child_dict = child.to_dict()

        assert child_dict['parent_category_id'] == parent.id


def test_category_repr(app):
    """Test __repr__ method"""
    with app.app_context():
        category = TransactionCategory(
            name='Transportation',
            icon='🚗',
            color='#8b5cf6'
        )
        assert repr(category) == '<TransactionCategory Transportation>'


def test_default_values(app):
    """Test default values are set correctly"""
    with app.app_context():
        category = TransactionCategory(
            name='Test',
            icon='🧪',
            color='#000000'
        )
        db.session.add(category)
        db.session.commit()

        # Verify defaults
        assert category.keywords == []
        assert category.is_system is True
        assert category.parent_category_id is None
        assert category.created_at is not None


def test_nullable_fields(app):
    """Test nullable fields can be None"""
    with app.app_context():
        category = TransactionCategory(
            name='Minimal',
            # icon and color can be nullable
        )
        db.session.add(category)
        db.session.commit()

        assert category.icon is None
        assert category.color is None
        assert category.parent_category_id is None

"""
Utility to seed default transaction categories.
"""
from app.database import db
from app.models.transaction_category import TransactionCategory


# 14 default categories with icons, colors, and keywords
DEFAULT_CATEGORIES = [
    {
        'name': 'Income',
        'icon': '💰',
        'color': '#10b981',
        'keywords': ['salary', 'freelance', 'interest', 'dividend']
    },
    {
        'name': 'Housing',
        'icon': '🏠',
        'color': '#3b82f6',
        'keywords': ['rent', 'mortgage', 'maintenance', 'property tax']
    },
    {
        'name': 'Utilities',
        'icon': '⚡',
        'color': '#f59e0b',
        'keywords': ['electricity', 'water', 'internet', 'phone', 'mobile']
    },
    {
        'name': 'Groceries',
        'icon': '🛒',
        'color': '#10b981',
        'keywords': ['grocery', 'supermarket', 'bigbasket', 'grofers', 'blinkit']
    },
    {
        'name': 'Dining',
        'icon': '🍽️',
        'color': '#ef4444',
        'keywords': ['restaurant', 'swiggy', 'zomato', 'food delivery', 'cafe']
    },
    {
        'name': 'Transportation',
        'icon': '🚗',
        'color': '#8b5cf6',
        'keywords': ['fuel', 'petrol', 'uber', 'ola', 'metro', 'bus']
    },
    {
        'name': 'Shopping',
        'icon': '🛍️',
        'color': '#ec4899',
        'keywords': ['amazon', 'flipkart', 'myntra', 'clothing', 'electronics']
    },
    {
        'name': 'Healthcare',
        'icon': '🏥',
        'color': '#ef4444',
        'keywords': ['doctor', 'hospital', 'pharmacy', 'medicine', 'insurance']
    },
    {
        'name': 'Entertainment',
        'icon': '🎬',
        'color': '#a855f7',
        'keywords': ['netflix', 'prime', 'movie', 'cinema', 'spotify']
    },
    {
        'name': 'Education',
        'icon': '📚',
        'color': '#3b82f6',
        'keywords': ['course', 'book', 'tuition', 'school', 'college']
    },
    {
        'name': 'Insurance',
        'icon': '🛡️',
        'color': '#6366f1',
        'keywords': ['insurance', 'premium', 'policy']
    },
    {
        'name': 'Investments',
        'icon': '📈',
        'color': '#059669',
        'keywords': ['mutual fund', 'sip', 'stock', 'investment']
    },
    {
        'name': 'Transfers',
        'icon': '↔️',
        'color': '#6b7280',
        'keywords': ['transfer', 'neft', 'imps', 'upi']
    },
    {
        'name': 'Uncategorized',
        'icon': '❓',
        'color': '#9ca3af',
        'keywords': []  # no keywords - catch-all category
    }
]


def seed_categories():
    """
    Create default transaction categories if they don't exist.

    Returns:
        int: Number of categories created
    """
    created_count = 0

    for category_data in DEFAULT_CATEGORIES:
        # Check if category already exists
        existing = TransactionCategory.query.filter_by(name=category_data['name']).first()

        if not existing:
            category = TransactionCategory(
                name=category_data['name'],
                icon=category_data['icon'],
                color=category_data['color'],
                keywords=category_data['keywords'],
                is_system=True
            )
            db.session.add(category)
            created_count += 1
            print(f"Created category: {category_data['name']}")
        else:
            print(f"Category already exists: {category_data['name']}")

    if created_count > 0:
        db.session.commit()
        print(f"\nSuccessfully created {created_count} categories")
    else:
        print("\nNo new categories created - all categories already exist")

    return created_count


if __name__ == '__main__':
    """Run as standalone script"""
    from app import create_app

    app = create_app()
    with app.app_context():
        print("Seeding transaction categories...")
        count = seed_categories()
        print(f"\nTotal categories in database: {TransactionCategory.query.count()}")

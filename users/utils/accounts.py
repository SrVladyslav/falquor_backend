from users.models import Account


def create_customer_account(email: str, data: dict[str, str]) -> Account:
    """Create a new Customer Account."""
    if not email:
        raise ValueError("Email is required")

    user, _ = Account.objects.update_or_create(
        email=email,  # Lookup by email
        defaults={
            "is_active": False,
            "is_admin": False,
            "is_staff": False,
            "is_superuser": False,
            # Customers information
            "first_name": data.get("name"),
            "last_name": data.get("surname"),
            "account_type": Account.AccountType.PERSONAL,
            "preferred_locale": data.get("locale", Account.AllowedLocales.EN),
        },
    )
    user.save()
    return user

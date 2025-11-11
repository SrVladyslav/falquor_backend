from customers.models import WorkshopCustomer
from users.models import Account


def map_workshop_customer_to_account(
    customer: WorkshopCustomer,
    is_active: bool = False,
    is_admin: bool = False,
    is_staff: bool = False,
    is_superuser: bool = False,
) -> tuple[Account, bool]:
    if not customer:
        return None

    account, created = Account.objects.update_or_create(
        email=customer.email,
        defaults={
            "first_name": customer.name,
            "last_name": customer.surname,
            "account_type": Account.AccountType.PERSONAL,
            "preferred_locale": Account.AllowedLocales.EN,
            "is_active": is_active,
            "is_admin": is_admin,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
        },
    )
    return account, created

import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from users.models import Account
from django.db import transaction
from django.conf import settings

# CUSTOMER = "CUSTOMER", "Customer"
#     BUSINESS_OWNER = "BUSINESS_OWNER", "Business Owner"
#     ADMIN = "ADMIN", "Admin"


class Command(BaseCommand):
    help = "Inicializa permisos desde un archivo JSON con IDs fijos"

    def handle(self, *args, **options):
        json_path = os.path.join(
            settings.BASE_DIR, "users", "fixtures", "permissions.json"
        )

        if not os.path.exists(json_path):
            self.stderr.write(
                self.style.ERROR(f"No se encontró el archivo {json_path}")
            )
            return

        with open(json_path, "r", encoding="utf-8") as f:
            permissions_data = json.load(f)

        content_type = ContentType.objects.get_for_model(Account)

        with transaction.atomic():
            for perm in permissions_data:
                obj, created = Permission.objects.update_or_create(
                    id=perm["id"],
                    defaults={
                        "codename": perm["codename"],
                        "name": perm["name"],
                        "content_type": content_type,
                    },
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{'Creado' if created else 'Actualizado'}: {perm['codename']} (id={perm['id']})"
                    )
                )

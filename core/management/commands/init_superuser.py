from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class Command(BaseCommand):
    help = "Create a superuser and apply migrations"

    def handle(self, *args, **kwargs):
        # Create superuser if it doesn't exist
        username = settings.SUPERUSER_USERNAME
        email = settings.SUPERUSER_EMAIL
        password = settings.SUPERUSER_PASSWORD

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email, username=username, password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'[BACKEND] Superuser "{email}" created successfully.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'[BACKEND] Superuser "{email}" already exists.')
            )

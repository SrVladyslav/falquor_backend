from django.core.management.base import BaseCommand
from nanoid import generate


class Command(BaseCommand):
    help = "Create a superuser and apply migrations"

    def handle(self, *args, **kwargs):
        # Create superuser if it doesn't exist
        print(generate(size=12))

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a default superuser if none exists (safe to run repeatedly).'

    def handle(self, *args, **kwargs):
        username = os.getenv('DEFAULT_SUPERUSER_USERNAME', 'superadmin')
        email = os.getenv('DEFAULT_SUPERUSER_EMAIL', 'admin@gmail.com')
        password = os.getenv('DEFAULT_SUPERUSER_PASSWORD', 'Welcome@123')

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'Superuser "{username}" already exists — skipping.'
            ))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role='admin',
            must_change_password=False,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Superuser "{username}" created successfully.'
        ))
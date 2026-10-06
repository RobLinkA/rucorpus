"""Create (or reset) administrator accounts.

    python manage.py create_admins administrator
"""
import getpass

from django.core.management.base import BaseCommand
from django.contrib.auth.password_validation import validate_password

from corpus.models import User


class Command(BaseCommand):
    help = 'Create or reset administrator accounts'

    def add_arguments(self, parser):
        parser.add_argument('usernames', nargs='+')
        parser.add_argument('--password', help='omit to be prompted')

    def handle(self, usernames, password=None, **opts):
        password = password or getpass.getpass('password: ')
        for name in usernames:
            user, created = User.objects.get_or_create(username=name)
            user.role = User.Role.ADMIN
            user.is_staff = user.is_active = True
            validate_password(password, user)
            user.set_password(password)
            user.save()
            self.stdout.write(f"{'created' if created else 'updated'} admin {name}")

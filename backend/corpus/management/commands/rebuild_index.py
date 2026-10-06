from django.core.management.base import BaseCommand

from corpus import fts


class Command(BaseCommand):
    help = 'Rebuild the full-text search index'

    def handle(self, **opts):
        fts.rebuild()
        self.stdout.write(self.style.SUCCESS('search index rebuilt'))

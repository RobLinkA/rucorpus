"""Run the AI annotators (re-runnable: the previous AI run is undone first).

    python manage.py ai_annotate
"""
from django.core.management.base import BaseCommand, CommandError
from corpus.models import Corpus

from corpus.ai.run import run


class Command(BaseCommand):
    help = 'Add AI annotations (marked origin=ai) and correct clear human slips'

    def add_arguments(self, parser):
        parser.add_argument('--corpus', type=int, help='limit built-in methods to one corpus ID')

    def handle(self, corpus=None, **opts):
        if corpus is not None and not Corpus.objects.filter(id=corpus).exists():
            raise CommandError('Corpus does not exist')
        report = run(progress=lambda msg: self.stdout.write(f'  {msg}'), corpus_id=corpus)
        self.stdout.write(self.style.SUCCESS(
            f"AI annotations: +{report['added']} added, {report['corrected']} corrections "
            f"(previous run undone: {report['undone_previous']})"))
        for row in report['labels']:
            agree = f"{row['agreement']:.0%}" if row['agreement'] is not None else '—'
            self.stdout.write(f"  [{row['corpus_id']}] {row['group']}:{row['label']:<14} "
                              f"+{row['added']:<5} fix {row['corrected']:<4} 覆盖人工 {agree}")

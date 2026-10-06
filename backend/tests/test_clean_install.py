"""Verify a fresh installation independently of all synthetic corpus fixtures."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_migrations_start_with_no_corpus_annotations_or_accounts(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'DJANGO_DB_PATH': str(tmp_path / 'empty.sqlite3'),
           'DJANGO_MEDIA_ROOT': str(tmp_path / 'media'), 'DJANGO_DEBUG': '1'}
    subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'],
                   cwd=backend, env=env, check=True, capture_output=True)
    code = """
import django, json
django.setup()
from corpus.models import Corpus, Segment, AnnotationGroup, AnnotationValue, SegmentAnnotation, User
from django.test import Client
print(json.dumps([model.objects.count() for model in
    (Corpus, Segment, AnnotationGroup, AnnotationValue, SegmentAnnotation, User)]))
client = Client()
assert client.get('/api/meta').json() == {'corpora': []}
assert client.get('/api/stats').json()['segments'] == 0
assert client.get('/api/search', {'q': 'reader'}).json()['total'] == 0
"""
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    result = subprocess.run([sys.executable, '-c', code], cwd=backend, env=env,
                            check=True, capture_output=True, text=True)
    assert json.loads(result.stdout.strip()) == [0, 0, 0, 0, 0, 0]

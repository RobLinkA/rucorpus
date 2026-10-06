"""Disposable invented test records. Never load a real corpus or user database."""
import json

import pytest
from django.core.management import call_command
from django.test import Client


def synthetic_dataset():
    data = {key: [] for key in ('corpora', 'versions', 'annotation_groups', 'works',
                                'paragraphs', 'groups', 'segments')}
    samples = [
        ('ru', 'zh', [('Один человек вошёл.', '一个人走进来了。'),
                      ('Два человека идут домой.', '两个人回家。'),
                      ('Увидев друга, он сказал привет.', '他看到朋友，说了你好。')]),
        ('en', 'fr', [('The reader walks home.', 'Le lecteur préfère l’été.'),
                      ('The readers walked home.', 'Une école près de la rivière.')]),
        ('es', 'zh', [('El niño lee poesía en el café.', '孩子读诗。'),
                      ('La canción es una alegría.', '这首歌令人快乐。')]),
    ]
    gid, sid = 0, 0
    for cid, (source_lang, target_lang, pairs) in enumerate(samples, 1):
        data['corpora'].append(dict(id=cid, name=f'Synthetic {source_lang}-{target_lang}',
            description='Invented for tests only', source_lang=source_lang, target_lang=target_lang,
            status='published', sort_order=cid))
        data['works'].append(dict(id=cid, corpus_id=cid, title_source=f'Test work {cid}',
            title_target=f'测试作品 {cid}', author='', sort_order=0))
        data['paragraphs'].append(dict(id=cid, work_id=cid, seq=0))
        for offset, kind in enumerate(('source', 'translation', 'translation')):
            vid = (cid - 1) * 3 + offset + 1
            data['versions'].append(dict(id=vid, corpus_id=cid, kind=kind,
                lang=source_lang if kind == 'source' else target_lang, label=f'Edition {vid}',
                person='', bibliography='', sort_order=offset))
        for seq, (source, target) in enumerate(pairs):
            gid += 1
            data['groups'].append(dict(id=gid, paragraph_id=cid, seq=seq))
            for offset in (1, 2):
                sid += 1
                annotations = []
                if cid == 1 and seq == 0 and offset == 1:
                    annotations = [1, 3]
                if cid == 1 and seq == 2 and offset == 1:
                    annotations = [5]  # An intentional conflict exercises replacement provenance.
                data['segments'].append(dict(id=sid, group_id=gid,
                    version_id=(cid - 1) * 3 + offset + 1, seq=seq, source=source,
                    target=target, unsplit=False, annotations=annotations))
    for group_id, name, labels in (
        (1, '翻译技巧', [(1, '增译'), (2, '减译'), (3, '断句法')]),
        (2, '副动词', [(4, '完成体副动词'), (5, '未完成体副动词')]),
        (3, '外部研究', [(6, '测试标签')]),
    ):
        data['annotation_groups'].append(dict(id=group_id, corpus_id=1, key=f'test-{group_id}',
            name=name, widget='checkbox', sort_order=group_id,
            values=[dict(id=vid, label=label, sort_order=i, legacy_defined=False)
                    for i, (vid, label) in enumerate(labels)]))
    return data


@pytest.fixture
def dataset(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / 'media'
    path = tmp_path / 'invented.json'
    path.write_text(json.dumps(synthetic_dataset(), ensure_ascii=False), encoding='utf-8')
    call_command('load_corpus', str(path), verbosity=0)
    call_command('ai_annotate', corpus=1, verbosity=0)
    from corpus.models import User
    for name, role in (('admin', 'admin'), ('editor', 'editor'), ('reader', 'user')):
        user = User.objects.create(username=name, role=role)
        user.set_password('test-only-password-42')
        user.save()


@pytest.fixture
def anon():
    return Client()


def _login(name):
    client = Client(enforce_csrf_checks=True)
    client.get('/api/auth/session')
    client.defaults['HTTP_X_CSRFTOKEN'] = client.cookies['csrftoken'].value
    response = client.post('/api/auth/login', json.dumps({
        'username': name, 'password': 'test-only-password-42'}), content_type='application/json')
    assert response.status_code == 200
    client.defaults['HTTP_X_CSRFTOKEN'] = client.cookies['csrftoken'].value
    return client


@pytest.fixture
def admin(dataset):
    return _login('admin')


@pytest.fixture
def editor(dataset):
    return _login('editor')


@pytest.fixture
def reader(dataset):
    return _login('reader')

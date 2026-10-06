import unicodedata

import pytest

from corpus.text import Highlighter, lemmas, parse_query, surface_tokens

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('dataset')]


@pytest.mark.parametrize(('query', 'total'), [
    ('reader', 1), ('readers', 1), ('READ*', 2), ('walk', 0), ('walk*', 2),
    ('"reader walks"', 1), ('"walks reader"', 0),
    ('école', 1), ('ÉCOLE', 1), ('ecole', 0), ('"préfère l’été"', 1),
    ("l'été", 1), ('niño', 1), ('nino', 0), ('poesía', 1), ('café', 1),
    ('cafe', 0), ('"lee poesía"', 1), ('canci*', 1), ('一个人', 1),
])
def test_basic_language_search(anon, query, total):
    response = anon.get('/api/search', {'q': query})
    assert response.status_code == 200
    assert response.json()['total'] == total


def test_english_has_no_automatic_lemmas(anon):
    assert lemmas('walked') == ('walked',)
    assert anon.get('/api/search', {'q': 'reader', 'mode': 'morph'}).json()['total'] == 1
    assert anon.get('/api/search', {'q': 'reader', 'mode': 'exact'}).json()['total'] == 1


def test_russian_morphology_still_expands(anon):
    morph = anon.get('/api/search', {'q': 'человек'}).json()
    exact = anon.get('/api/search', {'q': 'человек', 'mode': 'exact'}).json()
    assert morph['total'] == 2 and exact['total'] == 1
    assert morph['results'][0]['source_hl']


def test_composed_and_decomposed_accents(anon):
    query = unicodedata.normalize('NFD', 'école')
    response = anon.get('/api/search', {'q': query}).json()
    assert response['total'] == 1
    assert surface_tokens(query) == 'école'


@pytest.mark.parametrize('text', ['Une école ici.', 'Une e\u0301cole ici.'])
def test_accent_highlight_offsets(text):
    highlighter = Highlighter(parse_query('école'), 'exact')
    spans = highlighter.spans(text)
    assert len(spans) == 1
    assert unicodedata.normalize('NFC', text[slice(*spans[0])]) == 'école'
    phrase = Highlighter(parse_query('"école ici"'), 'exact')
    assert unicodedata.normalize('NFC', text[slice(*phrase.spans(text)[0])]) == 'école ici'


def test_reindex_after_non_russian_text_edit(anon):
    from corpus import fts
    from corpus.models import Segment
    Segment.objects.filter(corpus_id=3).update(source='Une e\u0301cole ouvre.')
    fts.rebuild()
    results = anon.get('/api/search', {'q': 'école', 'corpora': [3]}).json()
    assert results['total'] == 2
    spans = results['results'][0]['source_hl']
    assert spans and spans[0] == [4, 10]

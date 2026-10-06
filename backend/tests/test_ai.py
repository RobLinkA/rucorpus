import pytest

from corpus.ai.run import run, undo_previous
from corpus.models import SegmentAnnotation

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('dataset')]


def test_ai_evidence_replacement_and_repeatability():
    correction = SegmentAnnotation.objects.get(segment_id=5, value_id=4)
    assert correction.origin == 'ai' and correction.method == 'morph.fix'
    assert correction.replaced_id == 5 and 'Увидев' in correction.evidence
    assert not SegmentAnnotation.objects.filter(segment_id=5, value_id=5).exists()
    before = list(SegmentAnnotation.objects.filter(origin='ai').values_list(
        'segment_id', 'value_id', 'method', 'evidence', 'replaced_id'))
    undo_previous(corpus_id=1)
    assert SegmentAnnotation.objects.get(segment_id=5, value_id=5).origin == 'human'
    report = run(corpus_id=1)
    after = list(SegmentAnnotation.objects.filter(origin='ai').values_list(
        'segment_id', 'value_id', 'method', 'evidence', 'replaced_id'))
    assert before == after and report['corrected'] == 1


def test_external_annotations_survive_builtin_rerun():
    external = SegmentAnnotation.objects.create(segment_id=5, value_id=6,
        origin='ai', method='external.demo.v1', evidence='invented evidence', confidence='medium')
    run(corpus_id=1)
    assert SegmentAnnotation.objects.filter(id=external.id, method='external.demo.v1').exists()


def test_external_result_for_same_label_keeps_its_provenance():
    SegmentAnnotation.objects.filter(segment_id=6, value_id=4).delete()
    external = SegmentAnnotation.objects.create(segment_id=6, value_id=4,
        origin='ai', method='external.demo.v1', evidence='Увидев', confidence='medium')
    run(corpus_id=1)
    assert SegmentAnnotation.objects.get(segment_id=6, value_id=4).id == external.id


def test_external_wrong_label_is_not_treated_as_a_human_correction():
    external = SegmentAnnotation.objects.create(segment_id=6, value_id=5,
        origin='ai', method='external.demo.v1', evidence='test only', confidence='medium')
    run(corpus_id=1)
    assert SegmentAnnotation.objects.filter(id=external.id).exists()
    assert SegmentAnnotation.objects.get(segment_id=6, value_id=4).replaced_id is None


def test_other_corpora_untouched_when_scoped():
    correction_id = SegmentAnnotation.objects.get(segment_id=5, value_id=4).id
    report = run(corpus_id=2)
    assert report['added'] == 0 and report['corrected'] == 0
    assert SegmentAnnotation.objects.get(segment_id=5, value_id=4).id == correction_id


def test_optional_wordlist_not_required(monkeypatch):
    from corpus.ai import chinese
    monkeypatch.setattr(chinese, 'IDIOMS_PATH', '')
    chinese.idioms.cache_clear()
    chinese._jieba.cache_clear()
    assert chinese.idioms() == set()
    assert '跑来跑去' in chinese.four_character('孩子跑来跑去。')

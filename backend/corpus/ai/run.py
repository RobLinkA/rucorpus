"""AI annotation run: add machine annotations next to the human ones, and correct clear human slips.

Every row written here has origin='ai', the annotator name (method), the words it rests on
(evidence) and a confidence. Re-running first undoes the previous run (restoring any human value
an AI correction had replaced), so the result is reproducible.
"""
import collections
import json
from datetime import datetime

from django.conf import settings
from django.db import transaction

from ..models import AnnotationValue, Corpus, Segment, SegmentAnnotation
from . import chinese, morphology

METHODS = {
    'morph.nonfinite': {'label': '俄语词形分析（pymorphy3）', 'confidence': 'high',
                        'desc': '识别副动词、主动 / 被动形动词与命令式；只采用词典收录的词，排除人名与名词同形词。'},
    'morph.forms': {'label': '俄语词形分析（pymorphy3）', 'confidence': 'high',
                    'desc': '识别述谓词（含存在意义的 нет）、副动词、形动词，并判定体（完成 / 未完成）与长尾 / 短尾。'},
    'morph.fix': {'label': '人工标注更正', 'confidence': 'high',
                  'desc': '人工标注的体或长短尾与句中实际词形不符（如 увидев 被标为未完成体副动词），改为正确的值并保留原值。'},
    'syntax.definite': {'label': '依存句法分析（Natasha）', 'confidence': 'medium',
                        'desc': '无主语、谓语动词为第一人称或第二人称单数的分句，判为确定人称句。'},
    'zh.redup': {'label': '中文分词与结构规则（jieba）', 'confidence': 'high',
                 'desc': 'AA、ABB、AABB 式重叠词与 A了A、A一A 式动词重叠，排除亲属称谓等词汇化重叠。'},
    'zh.idiom': {'label': '成语词表与四字格式', 'confidence': 'high',
                 'desc': '可选的本地成语词表与“X来X去”“不X不Y”等能产四字格式。'},
    'zh.sound': {'label': '象声词词表', 'confidence': 'high', 'desc': '常见象声词（哗啦、扑通、嘎吱等）。'},
}

FORM_FAMILIES = ('副动词', '主动形动词', '被动形动词')


def _value_lookup():
    out = {}
    for v in AnnotationValue.objects.select_related('group'):
        out[(v.group.corpus_id, v.group.name, v.label)] = v.id
    return out


def undo_previous(corpus_id=None):
    """Refresh only built-in methods in scope; preserve third-party AI results."""
    rows = SegmentAnnotation.objects.filter(origin='ai', method__in=METHODS)
    if corpus_id is not None:
        rows = rows.filter(segment__corpus_id=corpus_id)
    restored = []
    for row in rows.exclude(replaced=None):
        restored.append(SegmentAnnotation(segment_id=row.segment_id, value_id=row.replaced_id))
    n, _ = rows.delete()
    SegmentAnnotation.objects.bulk_create(restored, ignore_conflicts=True)
    return n


def _ru_side(corpus):
    if corpus.source_lang == 'ru':
        return 'source'
    if corpus.target_lang == 'ru':
        return 'target'
    return None


def _detections(corpus, seg, groups, syntax_cache):
    """Yield (group, label, evidence words, method) for one segment."""
    ru = getattr(seg, _ru_side(corpus)) if _ru_side(corpus) else ''
    zh_side = 'target' if corpus.target_lang == 'zh' else ('source' if corpus.source_lang == 'zh' else None)
    zh = getattr(seg, zh_side) if zh_side else ''
    if ru and '非变位形式' in groups:
        for label, ws in morphology.nonfinite_forms(ru).items():
            yield '非变位形式', label, ws, 'morph.nonfinite'
    if ru and groups & {'述谓词', *FORM_FAMILIES}:
        for (g, label), ws in morphology.verbal_forms(ru).items():
            if g in groups:
                yield g, label, ws, 'morph.forms'
    if ru and '单部句类型' in groups:
        from . import syntax
        if ru not in syntax_cache:
            syntax_cache[ru] = syntax.classify(ru)
        if '确定人称句' in syntax_cache[ru]:
            yield '单部句类型', '确定人称句', syntax_cache[ru]['确定人称句'], 'syntax.definite'
    if zh and '译文修辞' in groups:
        for label, fn, method in (('叠词', chinese.reduplication, 'zh.redup'),
                                  ('四字格', chinese.four_character, 'zh.idiom'),
                                  ('象声词', chinese.onomatopoeia, 'zh.sound')):
            ws = fn(zh)
            if ws:
                yield '译文修辞', label, ws, method


def _corrections(corpus_id, human_labels, detected):
    """Aspect-based schemes: (wrong label, right label) pairs for one segment.
    Only clear cases: human says 未完成体 but the sentence has only the perfective form of that
    type, or long/short form swapped within the same aspect."""
    out = []
    for (g, label) in human_labels:
        if g not in FORM_FAMILIES or (g, label) in detected:
            continue
        same = [d for d in detected if d[0] == g and d not in human_labels]
        if len(same) != 1:
            continue
        right = same[0][1]
        flipped_aspect = label.startswith('未完成体') and right.startswith('完成体') and label[3:] == right[2:]
        flipped_tail = label[:-2] == right[:-2] and label[-2:] in ('长尾', '短尾') and right[-2:] in ('长尾', '短尾')
        if flipped_aspect or flipped_tail:
            out.append((g, label, right))
    return out


@transaction.atomic
def run(progress=None, corpus_id=None):
    undone = undo_previous(corpus_id)
    values = _value_lookup()
    vlabel = {vid: key for key, vid in values.items()}
    human = collections.defaultdict(set)
    occupied = collections.defaultdict(set)
    for sid, vid in SegmentAnnotation.objects.values_list('segment_id', 'value_id'):
        occupied[sid].add(vid)
    for sid, vid in SegmentAnnotation.objects.filter(origin='human').values_list('segment_id', 'value_id'):
        human[sid].add(vid)
    new_rows, delete_human = [], []
    stats = collections.defaultdict(lambda: {'added': 0, 'human_total': 0, 'human_found': 0, 'corrected': 0})
    syntax_cache = {}
    corpora = Corpus.objects.all()
    if corpus_id is not None:
        corpora = corpora.filter(id=corpus_id)
    for corpus in corpora:
        groups = set(corpus.annotation_groups.values_list('name', flat=True))
        if not groups or not _ru_side(corpus) and 'zh' not in (corpus.source_lang, corpus.target_lang):
            continue
        segs = Segment.objects.filter(corpus=corpus).only('id', 'source', 'target').order_by('id')
        for i, seg in enumerate(segs.iterator(chunk_size=1000)):
            if progress and i % 2000 == 0:
                progress(f'{corpus.name}: {i}')
            dets = {}
            for g, label, ws, method in _detections(corpus, seg, groups, syntax_cache):
                key = (g, label)
                if key in dets:
                    dets[key][0].extend(w for w in ws if w not in dets[key][0])
                else:
                    dets[key] = [list(dict.fromkeys(ws)), method]
            have = {vlabel[v][1:] for v in human[seg.id] if v in vlabel}
            # agreement statistics for methods that can be compared with the human labels
            for g, label in have:
                if (corpus.id, g, label) in values:
                    st = stats[(corpus.id, g, label)]
                    st['human_total'] += 1
                    st['human_found'] += (g, label) in dets
            for g, wrong, right in _corrections(corpus.id, have, set(dets)):
                wrong_id, right_id = values[(corpus.id, g, wrong)], values[(corpus.id, g, right)]
                if right_id in occupied[seg.id]:
                    # An external method already owns this label; retain both its result
                    # and the human judgment instead of rewriting provenance.
                    continue
                if (g, right) not in dets:
                    # a second wrong label pointing at the same value: leave it untouched, so that
                    # every deleted human row is recorded in exactly one AI row (undo stays lossless)
                    continue
                delete_human.append((seg.id, wrong_id))
                ws, _ = dets.pop((g, right))
                new_rows.append(SegmentAnnotation(
                    segment_id=seg.id, value_id=right_id, origin='ai', method='morph.fix',
                    evidence='、'.join(ws)[:300], confidence='high', replaced_id=wrong_id))
                stats[(corpus.id, g, right)]['corrected'] += 1
            for (g, label), (ws, method) in dets.items():
                vid = values.get((corpus.id, g, label))
                if vid is None or vid in occupied[seg.id]:
                    continue
                new_rows.append(SegmentAnnotation(
                    segment_id=seg.id, value_id=vid, origin='ai', method=method,
                    evidence='、'.join(ws)[:300], confidence=METHODS[method]['confidence']))
                stats[(corpus.id, g, label)]['added'] += 1
    for sid, vid in delete_human:
        SegmentAnnotation.objects.filter(segment_id=sid, value_id=vid, origin='human').delete()
    SegmentAnnotation.objects.bulk_create(new_rows, batch_size=5000)
    report = {
        'generated_at': datetime.now().isoformat(timespec='seconds'), 'corpus_id': corpus_id,
        'undone_previous': undone, 'added': sum(1 for r in new_rows if not r.replaced_id),
        'corrected': sum(1 for r in new_rows if r.replaced_id),
        'methods': METHODS,
        'labels': [{'corpus_id': c, 'group': g, 'label': lab, **st,
                    'agreement': round(st['human_found'] / st['human_total'], 3) if st['human_total'] else None}
                   for (c, g, lab), st in sorted(stats.items()) if st['added'] or st['corrected']],
    }
    path = settings.MEDIA_ROOT / 'ai_annotation_report.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    return report


def load_report():
    path = settings.MEDIA_ROOT / 'ai_annotation_report.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None

"""Build API payloads for alignment groups."""
import collections

from .models import AlignGroup, Favorite, Segment, SegmentAnnotation
from .text import Highlighter


def ai_info(segment_ids):
    """{segment_id: {value_id: {method, evidence, confidence, replaced}}} for AI annotations."""
    out = collections.defaultdict(dict)
    for sid, vid, method, evidence, conf, replaced in SegmentAnnotation.objects.filter(
            segment_id__in=segment_ids, origin='ai').values_list('segment_id', 'value_id', 'method', 'evidence',
                                                                  'confidence', 'replaced_id'):
        out[sid][vid] = {'method': method, 'evidence': evidence, 'confidence': conf, 'replaced': replaced}
    return out


def group_payloads(group_ids, user=None, hit_segments=None, highlighter: Highlighter | None = None):
    """Payload for each group id, preserving order.

    group = {id, corpus_id, work_id, paragraph_id, paragraph_seq, seq, position, source, source_hl,
             rows: [{version_id, segments: [{id, source, target, target_hl, annotations, hit, unsplit}]}],
             favorite}
    """
    if not group_ids:
        return []
    groups = {g.id: g for g in AlignGroup.objects.filter(id__in=group_ids).select_related('paragraph')}
    segs = list(Segment.objects.filter(group_id__in=group_ids)
                .select_related('version').order_by('group_id', 'version__sort_order', 'seq'))
    anns = collections.defaultdict(list)
    for sid, vid in SegmentAnnotation.objects.filter(segment__group_id__in=group_ids) \
            .values_list('segment_id', 'value_id').order_by('value__group__sort_order', 'value__sort_order'):
        anns[sid].append(vid)
    ai = ai_info([s.id for s in segs])
    favs = set()
    if user is not None and user.is_authenticated:
        favs = set(Favorite.objects.filter(user=user, group_id__in=group_ids).values_list('group_id', flat=True))
    by_group = collections.defaultdict(list)
    for s in segs:
        by_group[s.group_id].append(s)
    out = []
    for gid in group_ids:
        g = groups.get(gid)
        if not g:
            continue
        rows = collections.OrderedDict()
        for s in by_group[gid]:
            rows.setdefault(s.version_id, []).append(s)
        # all translations cover the same source span, except where one translation omits a
        # sentence: show the most complete segmentation
        fullest = max(rows.values(), key=lambda ss: sum(len(s.source) for s in ss), default=[])
        source = ' '.join(s.source for s in fullest)
        hl = highlighter.spans if highlighter else (lambda _t: [])
        out.append({
            'id': g.id, 'corpus_id': g.corpus_id, 'work_id': g.work_id, 'paragraph_id': g.paragraph_id,
            'paragraph_seq': g.paragraph.seq, 'seq': g.seq, 'position': g.position,
            'source': source, 'source_hl': hl(source),
            'rows': [{'version_id': vid, 'segments': [{
                'id': s.id, 'source': s.source, 'target': s.target, 'target_hl': hl(s.target),
                'annotations': anns.get(s.id, []), 'ai': ai.get(s.id, {}), 'unsplit': s.unsplit,
                'hit': hit_segments is not None and s.id in hit_segments,
            } for s in ss]} for vid, ss in rows.items()],
            'favorite': gid in favs,
        })
    return out

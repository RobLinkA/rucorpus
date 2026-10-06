"""Back-office API. Editors (标注员) may edit segments and annotations; everything else is admin-only."""
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Count, Exists, F, Max, OuterRef, Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema
from ninja.errors import HttpError

from .. import fts
from ..models import (AlignGroup, AnnotationGroup, AnnotationValue, AuditLog, Corpus, Favorite, Paragraph,
                      SearchHistory, Segment, SegmentAnnotation, User, Version, Work)
from . import audit, require_admin, require_editor
from ..serialize import ai_info
from .auth import user_payload

router = Router(tags=['manage'])


# ---------------------------------------------------------------- dashboard
@router.get('/dashboard')
def dashboard(request):
    require_editor(request)
    corpora = []
    for c in Corpus.objects.all():
        segs = Segment.objects.filter(corpus=c)
        n = segs.count()
        annotated = segs.filter(Exists(SegmentAnnotation.objects.filter(segment=OuterRef('pk')))).count()
        corpora.append({'id': c.id, 'name': c.name, 'status': c.status,
                        'works': Work.objects.filter(corpus=c).count(),
                        'versions': Version.objects.filter(corpus=c).count(),
                        'groups': AlignGroup.objects.filter(corpus=c).count(), 'segments': n,
                        'annotated_segments': annotated,
                        'annotations': SegmentAnnotation.objects.filter(segment__corpus=c).count(),
                        'ai_annotations': SegmentAnnotation.objects.filter(segment__corpus=c, origin='ai').count(),
                        'unsplit': segs.filter(unsplit=True).count()})
    groups = [{'id': g.id, 'corpus_id': g.corpus_id, 'name': g.name,
               'usage': SegmentAnnotation.objects.filter(value__group=g).count()}
              for g in AnnotationGroup.objects.all()]
    return {
        'corpora': corpora, 'annotation_groups': groups,
        'users': {'total': User.objects.count(), 'active': User.objects.filter(is_active=True).count(),
                  'by_role': dict(User.objects.values('role').annotate(n=Count('id')).values_list('role', 'n'))},
        'activity': {'favorites': Favorite.objects.count(), 'searches': SearchHistory.objects.count()},
        'recent': [_log(x) for x in AuditLog.objects.select_related('user')[:12]],
    }


def _log(x):
    return {'id': x.id, 'user': x.user.username if x.user else None, 'action': x.action, 'target': x.target,
            'summary': x.summary, 'created_at': x.created_at}


@router.get('/audit')
def audit_log(request, page: int = 1, size: int = 50, action: str = '', user: str = ''):
    require_admin(request)
    qs = AuditLog.objects.select_related('user')
    if action:
        qs = qs.filter(action=action)
    if user:
        qs = qs.filter(user__username=user)
    return {'total': qs.count(), 'results': [_log(x) for x in qs[(page - 1) * size:page * size]]}


# ---------------------------------------------------------------- corpora
class CorpusIn(Schema):
    name: str
    description: str = ''
    source_lang: str = 'ru'
    target_lang: str = 'zh'
    status: str = 'published'
    sort_order: int = 0


def _corpus_out(c):
    return {'id': c.id, 'name': c.name, 'description': c.description, 'source_lang': c.source_lang,
            'target_lang': c.target_lang, 'status': c.status, 'sort_order': c.sort_order}


@router.get('/corpora')
def list_corpora(request):
    require_editor(request)
    return [_corpus_out(c) for c in Corpus.objects.all()]


@router.post('/corpora')
def create_corpus(request, data: CorpusIn):
    require_admin(request)
    c = Corpus.objects.create(**data.dict())
    audit(request, 'corpus.create', f'corpus:{c.id}', f'新建语料库 {c.name}')
    return _corpus_out(c)


@router.put('/corpora/{cid}')
def update_corpus(request, cid: int, data: CorpusIn):
    require_admin(request)
    c = get_object_or_404(Corpus, id=cid)
    for k, v in data.dict().items():
        setattr(c, k, v)
    c.save()
    audit(request, 'corpus.update', f'corpus:{c.id}', f'修改语料库 {c.name}（{c.get_status_display()}）')
    return _corpus_out(c)


@router.delete('/corpora/{cid}')
def delete_corpus(request, cid: int, confirm: str):
    require_admin(request)
    c = get_object_or_404(Corpus, id=cid)
    if confirm != c.name:
        raise HttpError(400, '请输入语料库名称以确认删除')
    seg_ids = list(Segment.objects.filter(corpus=c).values_list('id', flat=True))
    with transaction.atomic():
        c.delete()
        fts.remove_segments(seg_ids)
    audit(request, 'corpus.delete', f'corpus:{cid}', f'删除语料库 {c.name}（{len(seg_ids)} 句对）')
    return {'ok': True}


# ---------------------------------------------------------------- versions
class VersionIn(Schema):
    kind: str = 'translation'
    lang: str
    label: str
    person: str = ''
    bibliography: str = ''
    sort_order: int = 0


def _version_out(v):
    return {'id': v.id, 'corpus_id': v.corpus_id, 'kind': v.kind, 'lang': v.lang, 'label': v.label,
            'person': v.person, 'bibliography': v.bibliography, 'sort_order': v.sort_order,
            'segments': Segment.objects.filter(version=v).count()}


@router.get('/corpora/{cid}/versions')
def list_versions(request, cid: int):
    require_editor(request)
    return [_version_out(v) for v in Version.objects.filter(corpus_id=cid)]


@router.post('/corpora/{cid}/versions')
def create_version(request, cid: int, data: VersionIn):
    require_admin(request)
    get_object_or_404(Corpus, id=cid)
    v = Version.objects.create(corpus_id=cid, **data.dict())
    audit(request, 'version.create', f'version:{v.id}', f'新建版本 {v.label}')
    return _version_out(v)


@router.put('/versions/{vid}')
def update_version(request, vid: int, data: VersionIn):
    require_admin(request)
    v = get_object_or_404(Version, id=vid)
    for k, val in data.dict().items():
        setattr(v, k, val)
    v.save()
    audit(request, 'version.update', f'version:{v.id}', f'修改版本 {v.label}')
    return _version_out(v)


@router.delete('/versions/{vid}')
def delete_version(request, vid: int):
    require_admin(request)
    v = get_object_or_404(Version, id=vid)
    seg_ids = list(Segment.objects.filter(version=v).values_list('id', flat=True))
    with transaction.atomic():
        v.delete()
        AlignGroup.objects.filter(corpus_id=v.corpus_id).annotate(n=Count('segments')).filter(n=0).delete()
        fts.remove_segments(seg_ids)
    audit(request, 'version.delete', f'version:{vid}', f'删除版本 {v.label}（{len(seg_ids)} 句对）')
    return {'ok': True}


# ---------------------------------------------------------------- works
class WorkIn(Schema):
    title_source: str
    title_target: str = ''
    author: str = ''
    sort_order: int = 0


def _work_out(w):
    return {'id': w.id, 'corpus_id': w.corpus_id, 'title_source': w.title_source, 'title_target': w.title_target,
            'author': w.author, 'sort_order': w.sort_order,
            'paragraphs': Paragraph.objects.filter(work=w).count(),
            'groups': AlignGroup.objects.filter(work=w).count(),
            'segments': Segment.objects.filter(work=w).count()}


@router.get('/corpora/{cid}/works')
def list_works(request, cid: int):
    require_editor(request)
    return [_work_out(w) for w in Work.objects.filter(corpus_id=cid)]


@router.post('/corpora/{cid}/works')
def create_work(request, cid: int, data: WorkIn):
    require_admin(request)
    get_object_or_404(Corpus, id=cid)
    w = Work.objects.create(corpus_id=cid, **data.dict())
    audit(request, 'work.create', f'work:{w.id}', f'新建作品 {w.title_source}')
    return _work_out(w)


@router.put('/works/{wid}')
def update_work(request, wid: int, data: WorkIn):
    require_admin(request)
    w = get_object_or_404(Work, id=wid)
    for k, val in data.dict().items():
        setattr(w, k, val)
    w.save()
    audit(request, 'work.update', f'work:{w.id}', f'修改作品 {w.title_source}')
    return _work_out(w)


@router.delete('/works/{wid}')
def delete_work(request, wid: int):
    require_admin(request)
    w = get_object_or_404(Work, id=wid)
    seg_ids = list(Segment.objects.filter(work=w).values_list('id', flat=True))
    with transaction.atomic():
        w.delete()
        fts.remove_segments(seg_ids)
    audit(request, 'work.delete', f'work:{wid}', f'删除作品 {w.title_source}（{len(seg_ids)} 句对）')
    return {'ok': True}


class OrderIn(Schema):
    ids: list[int]


@router.post('/works/reorder')
def reorder_works(request, data: OrderIn):
    require_admin(request)
    for i, wid in enumerate(data.ids):
        Work.objects.filter(id=wid).update(sort_order=i)
    return {'ok': True}


# ---------------------------------------------------------------- annotation scheme
class GroupIn(Schema):
    name: str
    key: str = ''
    description: str = ''
    widget: str = 'checkbox'
    sort_order: int | None = None


class ValueIn(Schema):
    label: str
    sort_order: int | None = None


def _group_out(g):
    usage = dict(SegmentAnnotation.objects.filter(value__group=g).values('value_id')
                 .annotate(n=Count('id')).values_list('value_id', 'n'))
    return {'id': g.id, 'corpus_id': g.corpus_id, 'name': g.name, 'key': g.key, 'description': g.description,
            'widget': g.widget, 'sort_order': g.sort_order,
            'values': [{'id': v.id, 'label': v.label, 'sort_order': v.sort_order, 'usage': usage.get(v.id, 0),
                        'defined_in_legacy': v.defined_in_legacy} for v in g.values.all()]}


@router.get('/corpora/{cid}/annotation-groups')
def list_groups(request, cid: int):
    require_editor(request)
    return [_group_out(g) for g in AnnotationGroup.objects.filter(corpus_id=cid).prefetch_related('values')]


@router.post('/corpora/{cid}/annotation-groups')
def create_group(request, cid: int, data: GroupIn):
    require_admin(request)
    get_object_or_404(Corpus, id=cid)
    d = data.dict()
    if d['sort_order'] is None:
        d['sort_order'] = (AnnotationGroup.objects.filter(corpus_id=cid).aggregate(m=Max('sort_order'))['m'] or 0) + 1
    g = AnnotationGroup.objects.create(corpus_id=cid, **d)
    audit(request, 'scheme.group.create', f'annotation_group:{g.id}', f'新建标注组 {g.name}')
    return _group_out(g)


@router.put('/annotation-groups/{gid}')
def update_group(request, gid: int, data: GroupIn):
    require_admin(request)
    g = get_object_or_404(AnnotationGroup, id=gid)
    old = g.name
    for k, v in data.dict(exclude_none=True).items():
        setattr(g, k, v)
    g.save()
    audit(request, 'scheme.group.update', f'annotation_group:{g.id}', f'修改标注组 {old} → {g.name}')
    return _group_out(g)


@router.delete('/annotation-groups/{gid}')
def delete_group(request, gid: int):
    require_admin(request)
    g = get_object_or_404(AnnotationGroup, id=gid)
    n = SegmentAnnotation.objects.filter(value__group=g).count()
    g.delete()
    audit(request, 'scheme.group.delete', f'annotation_group:{gid}', f'删除标注组 {g.name}（{n} 条标注）')
    return {'ok': True}


@router.post('/annotation-groups/{gid}/values')
def create_value(request, gid: int, data: ValueIn):
    require_admin(request)
    g = get_object_or_404(AnnotationGroup, id=gid)
    order = data.sort_order if data.sort_order is not None else \
        (g.values.aggregate(m=Max('sort_order'))['m'] or 0) + 1
    v = AnnotationValue.objects.create(group=g, label=data.label.strip(), sort_order=order)
    audit(request, 'scheme.value.create', f'annotation_value:{v.id}', f'新建标注项 {g.name}:{v.label}')
    return _group_out(g)


@router.put('/annotation-values/{vid}')
def update_value(request, vid: int, data: ValueIn):
    require_admin(request)
    v = get_object_or_404(AnnotationValue, id=vid)
    old = v.label
    v.label = data.label.strip()
    if data.sort_order is not None:
        v.sort_order = data.sort_order
    v.save()
    audit(request, 'scheme.value.update', f'annotation_value:{v.id}', f'修改标注项 {old} → {v.label}')
    return _group_out(v.group)


@router.delete('/annotation-values/{vid}')
def delete_value(request, vid: int):
    require_admin(request)
    v = get_object_or_404(AnnotationValue, id=vid)
    n = SegmentAnnotation.objects.filter(value=v).count()
    g = v.group
    v.delete()
    audit(request, 'scheme.value.delete', f'annotation_value:{vid}', f'删除标注项 {g.name}:{v.label}（{n} 条标注）')
    return _group_out(g)


class MergeIn(Schema):
    into: int


@router.post('/annotation-values/{vid}/merge')
def merge_value(request, vid: int, data: MergeIn):
    """Move every use of value `vid` to value `into` (same corpus), then delete `vid`."""
    require_admin(request)
    src = get_object_or_404(AnnotationValue.objects.select_related('group'), id=vid)
    dst = get_object_or_404(AnnotationValue.objects.select_related('group'), id=data.into)
    if src.group.corpus_id != dst.group.corpus_id or src.id == dst.id:
        raise HttpError(400, '只能合并到同一语料库中的另一个标注项')
    with transaction.atomic():
        seg_ids = list(SegmentAnnotation.objects.filter(value=src).values_list('segment_id', flat=True))
        existing = set(SegmentAnnotation.objects.filter(value=dst, segment_id__in=seg_ids)
                       .values_list('segment_id', flat=True))
        SegmentAnnotation.objects.bulk_create([SegmentAnnotation(segment_id=s, value=dst)
                                               for s in seg_ids if s not in existing])
        src.delete()
    audit(request, 'scheme.value.merge', f'annotation_value:{vid}',
          f'合并标注项 {src.group.name}:{src.label} → {dst.group.name}:{dst.label}（{len(seg_ids)} 条）')
    return {'moved': len(seg_ids)}


@router.post('/annotation-groups/reorder')
def reorder_groups(request, data: OrderIn):
    require_admin(request)
    for i, gid in enumerate(data.ids):
        AnnotationGroup.objects.filter(id=gid).update(sort_order=i)
    return {'ok': True}


@router.post('/annotation-values/reorder')
def reorder_values(request, data: OrderIn):
    require_admin(request)
    for i, vid in enumerate(data.ids):
        AnnotationValue.objects.filter(id=vid).update(sort_order=i)
    return {'ok': True}


# ---------------------------------------------------------------- segments
class SegmentFilter(Schema):
    corpus: int
    work: int | None = None
    version: int | None = None
    q: str = ''
    value: int | None = None
    unannotated: bool = False
    unsplit: bool = False
    origin: str = ''
    page: int = 1
    size: int = 50


def _segment_qs(f: SegmentFilter):
    qs = Segment.objects.filter(corpus_id=f.corpus)
    if f.work:
        qs = qs.filter(work_id=f.work)
    if f.version:
        qs = qs.filter(version_id=f.version)
    if f.q.strip():
        t = f.q.strip()
        qs = qs.filter(Q(source__icontains=t) | Q(target__icontains=t) | (Q(id=int(t)) if t.isdigit() else Q()))
    if f.value:
        qs = qs.filter(annotations__id=f.value)
    if f.unannotated:
        qs = qs.filter(~Exists(SegmentAnnotation.objects.filter(segment=OuterRef('pk'))))
    if f.unsplit:
        qs = qs.filter(unsplit=True)
    if f.origin in ('ai', 'fix'):
        rows = SegmentAnnotation.objects.filter(segment=OuterRef('pk'), origin='ai')
        if f.value:
            rows = rows.filter(value_id=f.value)
        if f.origin == 'fix':
            rows = rows.exclude(replaced=None)
        qs = qs.filter(Exists(rows))
    return qs


def _segment_out(s, anns, ai):
    return {'ai': ai.get(s.id, {}),'id': s.id, 'group_id': s.group_id, 'work_id': s.work_id, 'version_id': s.version_id,
            'paragraph_seq': s.group.paragraph.seq, 'group_seq': s.group.seq, 'seq': s.seq,
            'source': s.source, 'target': s.target, 'unsplit': s.unsplit, 'annotations': anns.get(s.id, [])}


@router.get('/segments')
def list_segments(request, f: Query[SegmentFilter]):
    require_editor(request)
    qs = _segment_qs(f).order_by('work__sort_order', 'group__position', 'version__sort_order', 'seq')
    total = qs.count()
    size = min(max(f.size, 10), 200)
    items = list(qs.select_related('group__paragraph')[(f.page - 1) * size:f.page * size])
    anns = {}
    for sid, vid in SegmentAnnotation.objects.filter(segment_id__in=[s.id for s in items]) \
            .values_list('segment_id', 'value_id'):
        anns.setdefault(sid, []).append(vid)
    ai = ai_info([s.id for s in items])
    return {'total': total, 'page': f.page, 'size': size, 'results': [_segment_out(s, anns, ai) for s in items]}


class SegmentTextIn(Schema):
    source: str
    target: str


@router.put('/segments/{sid}')
def update_segment(request, sid: int, data: SegmentTextIn):
    require_editor(request)
    s = get_object_or_404(Segment, id=sid)
    if not data.source.strip():
        raise HttpError(400, '原文不能为空')
    old = (s.source, s.target)
    s.source, s.target = data.source.strip(), data.target.strip()
    s.save(update_fields=['source', 'target', 'updated_at'])
    fts.index_segments([(s.id, s.source, s.target)])
    audit(request, 'segment.edit', f'segment:{s.id}', f'修改句对 {s.id} 文本', before=old)
    return {'ok': True}


class SplitPart(Schema):
    source: str
    target: str


class SplitIn(Schema):
    parts: list[SplitPart]


@router.post('/segments/{sid}/split')
def split_segment(request, sid: int, data: SplitIn):
    """Replace one segment by several consecutive ones in the same alignment group
    (used to finish paragraphs the legacy data never split into sentences)."""
    require_editor(request)
    s = get_object_or_404(Segment, id=sid)
    parts = [p for p in data.parts if p.source.strip()]
    if len(parts) < 2:
        raise HttpError(400, '至少拆成两句')
    with transaction.atomic():
        later = Segment.objects.filter(group__paragraph_id=s.group.paragraph_id, version_id=s.version_id,
                                       seq__gt=s.seq)
        later.update(seq=F('seq') + len(parts) - 1)
        s.source, s.target, s.unsplit = parts[0].source.strip(), parts[0].target.strip(), False
        s.save()
        new = [Segment.objects.create(group_id=s.group_id, version_id=s.version_id, seq=s.seq + i,
                                      source=p.source.strip(), target=p.target.strip(), work_id=s.work_id,
                                      corpus_id=s.corpus_id) for i, p in enumerate(parts[1:], start=1)]
        fts.index_segments([(x.id, x.source, x.target) for x in [s] + new])
    audit(request, 'segment.split', f'segment:{sid}', f'句对 {sid} 拆分为 {len(parts)} 句')
    return {'ids': [s.id] + [x.id for x in new]}


class BatchAnnotateIn(Schema):
    segment_ids: list[int]
    add: list[int] = []
    remove: list[int] = []


@router.post('/segments/batch-annotate')
def batch_annotate(request, data: BatchAnnotateIn):
    require_editor(request)
    segs = Segment.objects.filter(id__in=data.segment_ids)
    corpus_ids = set(segs.values_list('corpus_id', flat=True))
    if len(corpus_ids) > 1:
        raise HttpError(400, '批量标注只能在同一语料库内进行')
    if AnnotationValue.objects.filter(id__in=data.add + data.remove).exclude(group__corpus_id__in=corpus_ids).exists():
        raise HttpError(400, '标注项不属于该语料库')
    ids = list(segs.values_list('id', flat=True))
    with transaction.atomic():
        removed, _ = SegmentAnnotation.objects.filter(segment_id__in=ids, value_id__in=data.remove).delete()
        existing = set(SegmentAnnotation.objects.filter(segment_id__in=ids, value_id__in=data.add)
                       .values_list('segment_id', 'value_id'))
        new = [SegmentAnnotation(segment_id=s, value_id=v) for s in ids for v in data.add if (s, v) not in existing]
        SegmentAnnotation.objects.bulk_create(new)
    audit(request, 'annotate.batch', f'segments:{len(ids)}',
          f'批量标注 {len(ids)} 句对：新增 {len(new)} 条，移除 {removed} 条', add=data.add, remove=data.remove)
    return {'added': len(new), 'removed': removed}


# ---------------------------------------------------------------- users
class UserIn(Schema):
    username: str
    display_name: str = ''
    institution: str = ''
    email: str = ''
    role: str = 'user'
    is_active: bool = True
    password: str | None = None


def _user_out(u):
    d = user_payload(u)
    d.update({'email': u.email, 'is_active': u.is_active, 'role': u.role, 'date_joined': u.date_joined,
              'last_login': u.last_login, 'favorites': u.favorites.count(), 'searches': u.searches.count()})
    return d


@router.get('/users')
def list_users(request, q: str = ''):
    require_admin(request)
    qs = User.objects.all().order_by('-date_joined')
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(display_name__icontains=q) | Q(institution__icontains=q))
    return [_user_out(u) for u in qs]


@router.post('/users')
def create_user(request, data: UserIn):
    require_admin(request)
    if User.objects.filter(username=data.username.strip()).exists():
        raise HttpError(400, '用户名已存在')
    if not data.password:
        raise HttpError(400, '请设置初始密码')
    validate_password(data.password)
    u = User(username=data.username.strip(), display_name=data.display_name, institution=data.institution,
             email=data.email, role=data.role, is_active=data.is_active)
    u.set_password(data.password)
    u.save()
    audit(request, 'user.create', f'user:{u.id}', f'新建用户 {u.username}（{u.get_role_display()}）')
    return _user_out(u)


@router.put('/users/{uid}')
def update_user(request, uid: int, data: UserIn):
    require_admin(request)
    u = get_object_or_404(User, id=uid)
    if u.id == request.user.id and (data.role != User.Role.ADMIN or not data.is_active):
        raise HttpError(400, '不能取消自己的管理员权限或停用自己')
    for k in ('display_name', 'institution', 'email', 'role', 'is_active'):
        setattr(u, k, getattr(data, k))
    if data.password:
        validate_password(data.password, u)
        u.set_password(data.password)
    u.save()
    audit(request, 'user.update', f'user:{u.id}', f"修改用户 {u.username}{'（重置密码）' if data.password else ''}")
    return _user_out(u)


@router.delete('/users/{uid}')
def delete_user(request, uid: int):
    require_admin(request)
    u = get_object_or_404(User, id=uid)
    if u.id == request.user.id:
        raise HttpError(400, '不能删除自己')
    u.delete()
    audit(request, 'user.delete', f'user:{uid}', f'删除用户 {u.username}')
    return {'ok': True}

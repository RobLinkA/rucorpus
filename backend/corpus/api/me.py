from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema

from ..models import AlignGroup, Favorite, SearchHistory
from ..serialize import group_payloads
from .public import export_groups, visible_corpora

router = Router(tags=['me'])


class FavoriteFilter(Schema):
    corpus: int | None = None
    work: int | None = None
    values: list[int] = []
    q: str = ''
    page: int = 1
    size: int = 20


def _favorites(request, f: FavoriteFilter):
    qs = Favorite.objects.filter(user=request.user, group__corpus__in=visible_corpora(request))
    if f.corpus:
        qs = qs.filter(group__corpus_id=f.corpus)
    if f.work:
        qs = qs.filter(group__work_id=f.work)
    for v in f.values:  # all selected annotation values must appear in the group
        qs = qs.filter(group__segments__annotations__id=v)
    if f.q.strip():
        t = f.q.strip()
        qs = qs.filter(Q(note__icontains=t) | Q(group__segments__source__icontains=t) |
                       Q(group__segments__target__icontains=t))
    return qs.distinct()


@router.get('/favorites')
def list_favorites(request, f: Query[FavoriteFilter]):
    qs = _favorites(request, f)
    total = qs.count()
    size = min(max(f.size, 5), 100)
    favs = list(qs.order_by('-created_at')[(f.page - 1) * size:f.page * size])
    payloads = {g['id']: g for g in group_payloads([x.group_id for x in favs], request.user)}
    return {'total': total, 'page': f.page, 'size': size,
            'results': [{'id': x.id, 'note': x.note, 'created_at': x.created_at, 'group': payloads.get(x.group_id)}
                        for x in favs]}


@router.get('/favorites/ids')
def favorite_group_ids(request):
    return list(Favorite.objects.filter(user=request.user).values_list('group_id', flat=True))


class FavoriteIn(Schema):
    group_id: int
    note: str = ''


@router.post('/favorites')
def add_favorite(request, data: FavoriteIn):
    group = get_object_or_404(AlignGroup, id=data.group_id, corpus__in=visible_corpora(request))
    fav, _ = Favorite.objects.get_or_create(user=request.user, group=group, defaults={'note': data.note})
    return {'id': fav.id, 'group_id': group.id}


class NoteIn(Schema):
    note: str


@router.get('/favorites/by-group/{group_id}')
def get_favorite(request, group_id: int):
    fav = get_object_or_404(Favorite, user=request.user, group_id=group_id)
    return {'id': fav.id, 'note': fav.note, 'created_at': fav.created_at}


@router.put('/favorites/by-group/{group_id}')
def update_note(request, group_id: int, data: NoteIn):
    fav = get_object_or_404(Favorite, user=request.user, group_id=group_id)
    fav.note = data.note[:5000]
    fav.save(update_fields=['note'])
    return {'ok': True}


@router.delete('/favorites/by-group/{group_id}')
def remove_favorite(request, group_id: int):
    Favorite.objects.filter(user=request.user, group_id=group_id).delete()
    return {'ok': True}


@router.get('/favorites/export')
def export_favorites(request, f: Query[FavoriteFilter], format: str = 'xlsx'):
    favs = list(_favorites(request, f).order_by('-created_at').values_list('group_id', 'note'))
    return export_groups([g for g, _ in favs], '我的收藏', format, notes=dict(favs))


@router.get('/history')
def list_history(request, page: int = 1, size: int = 30):
    qs = SearchHistory.objects.filter(user=request.user)
    total = qs.count()
    items = qs[(page - 1) * size:page * size]
    return {'total': total, 'results': [{
        'id': h.id, 'params': h.params, 'summary': h.summary, 'result_count': h.result_count, 'name': h.name,
        'pinned': h.pinned, 'created_at': h.created_at} for h in items]}


class HistoryPatch(Schema):
    name: str | None = None
    pinned: bool | None = None


@router.patch('/history/{hid}')
def update_history(request, hid: int, data: HistoryPatch):
    h = get_object_or_404(SearchHistory, id=hid, user=request.user)
    if data.name is not None:
        h.name = data.name[:200]
    if data.pinned is not None:
        h.pinned = data.pinned
    h.save()
    return {'ok': True}


@router.delete('/history/{hid}')
def delete_history(request, hid: int):
    SearchHistory.objects.filter(id=hid, user=request.user).delete()
    return {'ok': True}


@router.delete('/history')
def clear_history(request, keep_pinned: bool = True):
    qs = SearchHistory.objects.filter(user=request.user)
    if keep_pinned:
        qs = qs.filter(pinned=False)
    n, _ = qs.delete()
    return {'deleted': n}

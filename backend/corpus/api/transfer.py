"""Import / export endpoints. Imports are two-step: upload → preview (nothing written) → commit."""
from urllib.parse import quote

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from .. import transfer as T
from ..models import Corpus, ImportJob
from . import audit, require_admin, require_editor

router = Router(tags=['transfer'])
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _download(content, name, ctype):
    resp = HttpResponse(content, content_type=ctype)
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(name)}"
    return resp


@router.get('/export/{cid}')
def export_corpus(request, cid: int, format: str = 'xlsx', works: str = ''):
    require_editor(request)
    corpus = get_object_or_404(Corpus, id=cid)
    work_ids = [int(x) for x in works.split(',') if x.isdigit()] or None
    if format == 'csv':
        groups = list(corpus.annotation_groups.prefetch_related('values'))
        ws = corpus.works.filter(id__in=work_ids) if work_ids else corpus.works.all()
        rows = [T.FIXED + [g.name for g in groups]] + T.segment_rows(corpus, groups, ws)
        return _download(T.csv_bytes(rows), f'{corpus.name}.csv', 'text/csv; charset=utf-8')
    return _download(T.corpus_workbook(corpus, True, work_ids), f'{corpus.name}.xlsx', XLSX)


@router.get('/template/{cid}')
def template(request, cid: int):
    require_editor(request)
    corpus = get_object_or_404(Corpus, id=cid)
    return _download(T.corpus_workbook(corpus, with_data=False), f'{corpus.name}-模板.xlsx', XLSX)


def _job_out(j):
    return {'id': j.id, 'kind': j.kind, 'filename': j.filename, 'status': j.status, 'preview': j.preview,
            'result': j.result, 'created_at': j.created_at, 'user': j.user.username if j.user else None}


@router.get('/jobs')
def list_jobs(request):
    require_editor(request)
    return [_job_out(j) for j in ImportJob.objects.select_related('user')[:30]]


def _plan(job):
    job.file.open('rb')
    content = job.file.read()
    job.file.close()
    tables = T.read_tables(job.filename, content)
    corpus = Corpus.objects.filter(id=job.preview.get('corpus_id')).first()
    if job.kind == 'annotations':
        return T.plan_annotations(corpus, tables, job.preview.get('update_text', False))
    return T.plan_corpus(tables, corpus)


@router.post('/upload')
def upload(request, kind: Form[str], file: File[UploadedFile], corpus_id: Form[int] = 0,
           update_text: Form[bool] = False):
    if kind == 'annotations':
        require_editor(request)
        if not corpus_id:
            raise HttpError(400, '请选择语料库')
    elif kind == 'corpus':
        require_admin(request)
    else:
        raise HttpError(400, '未知的导入类型')
    if file.size > 50 * 1024 * 1024:
        raise HttpError(400, '文件不能超过 50MB')
    content = file.read()
    job = ImportJob(user=request.user, kind=kind, filename=file.name,
                    preview={'corpus_id': corpus_id or None, 'update_text': update_text})
    job.file.save(file.name, ContentFile(content), save=False)
    try:
        summary, plan, errors = _plan(job)
    except T.FileError as e:
        raise HttpError(400, str(e))
    job.preview.update({'summary': summary, 'error_count': len(errors), 'errors': errors[:200],
                        'sample': plan[:20] if isinstance(plan, list) else None})
    job.save()
    return _job_out(job)


@router.post('/jobs/{jid}/commit')
def commit(request, jid: int):
    job = get_object_or_404(ImportJob, id=jid)
    (require_editor if job.kind == 'annotations' else require_admin)(request)
    if job.status != ImportJob.Status.PREVIEW:
        raise HttpError(400, '该导入任务已处理')
    summary, plan, errors = _plan(job)
    if job.kind == 'annotations':
        T.apply_annotations(plan)
        job.result = {'applied_segments': len(plan), 'skipped_rows': len({r for r, _ in errors}),
                      'annotations_added': summary['annotations_added'],
                      'annotations_removed': summary['annotations_removed'], 'text_updates': summary['text_updates']}
        audit(request, 'import.annotations', f'import:{job.id}',
              f"导入标注 {job.filename}：{len(plan)} 句对变更，新增 {summary['annotations_added']}，"
              f"移除 {summary['annotations_removed']}，跳过 {job.result['skipped_rows']} 行")
    else:
        if errors:
            raise HttpError(400, f'文件有 {len(errors)} 处错误，请修正后重新上传')
        target = Corpus.objects.filter(id=job.preview.get('corpus_id')).first()
        corpus, n = T.apply_corpus(plan, target)
        job.result = {'corpus_id': corpus.id, 'segments': n, 'works': summary['works']}
        audit(request, 'import.corpus', f'corpus:{corpus.id}',
              f"导入语料 {job.filename} → {corpus.name}：{summary['works']} 部作品，{n} 句对")
    job.status = ImportJob.Status.DONE
    job.save()
    return _job_out(job)


@router.post('/jobs/{jid}/cancel')
def cancel(request, jid: int):
    require_editor(request)
    job = get_object_or_404(ImportJob, id=jid, status=ImportJob.Status.PREVIEW)
    job.status = ImportJob.Status.CANCELLED
    job.save()
    return _job_out(job)


@router.get('/jobs/{jid}/errors')
def job_errors(request, jid: int):
    require_editor(request)
    job = get_object_or_404(ImportJob, id=jid)
    _, _, errors = _plan(job)
    return _download(T.csv_bytes([['行号', '问题']] + [list(e) for e in errors]),
                     f'{job.filename}-错误明细.csv', 'text/csv; charset=utf-8')

"""Initialize a database from canonical JSON; see DATA_ANNOTATION_GUIDE.md.

    python manage.py load_corpus /path/to/your-corpus.json [--replace]

IDs are supplied by the caller. No corpus or annotation data is bundled.
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from corpus import fts
from corpus.models import (AlignGroup, AnnotationGroup, AnnotationValue, Corpus, Paragraph, Segment,
                           SegmentAnnotation, Version, Work)


class Command(BaseCommand):
    help = 'Load corpus data from a canonical JSON file'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('--replace', action='store_true', help='delete existing corpus data first')

    def handle(self, path, replace=False, **opts):
        with open(path, encoding='utf-8') as file:
            data = json.load(file)
        if Corpus.objects.exists() and not replace:
            raise CommandError('Database already has corpus data; use --replace to overwrite it.')
        with transaction.atomic():
            if replace:
                Corpus.objects.all().delete()
            Corpus.objects.bulk_create([Corpus(
                id=c['id'], name=c['name'], description=c['description'], source_lang=c['source_lang'],
                target_lang=c['target_lang'], status=c['status'], sort_order=c['sort_order'],
            ) for c in data['corpora']])
            Version.objects.bulk_create([Version(
                id=v['id'], corpus_id=v['corpus_id'], kind=v['kind'], lang=v['lang'], label=v['label'],
                person=v['person'], bibliography=v['bibliography'], sort_order=v['sort_order'],
            ) for v in data['versions']])
            groups, values = [], []
            for g in data['annotation_groups']:
                groups.append(AnnotationGroup(id=g['id'], corpus_id=g['corpus_id'], key=g['key'], name=g['name'],
                                              widget=g['widget'], sort_order=g['sort_order']))
                values += [AnnotationValue(id=v['id'], group_id=g['id'], label=v['label'], sort_order=v['sort_order'],
                                           defined_in_legacy=v.get('legacy_defined', False)) for v in g['values']]
            AnnotationGroup.objects.bulk_create(groups)
            AnnotationValue.objects.bulk_create(values)
            Work.objects.bulk_create([Work(
                id=w['id'], corpus_id=w['corpus_id'], title_source=w['title_source'],
                title_target=w['title_target'], author=w['author'], sort_order=w['sort_order'],
            ) for w in data['works']])
            work_corpus = {w['id']: w['corpus_id'] for w in data['works']}
            Paragraph.objects.bulk_create([Paragraph(id=p['id'], work_id=p['work_id'], seq=p['seq'])
                                           for p in data['paragraphs']], batch_size=2000)
            para_work = {p['id']: p['work_id'] for p in data['paragraphs']}
            para_seq = {p['id']: p['seq'] for p in data['paragraphs']}
            ordered = sorted(data['groups'], key=lambda g: (para_work[g['paragraph_id']], para_seq[g['paragraph_id']], g['seq']))
            position, last_work, objs = 0, None, []
            for g in ordered:
                wid = para_work[g['paragraph_id']]
                position = 0 if wid != last_work else position + 1
                last_work = wid
                objs.append(AlignGroup(id=g['id'], paragraph_id=g['paragraph_id'], seq=g['seq'], work_id=wid,
                                       corpus_id=work_corpus[wid], position=position))
            AlignGroup.objects.bulk_create(objs, batch_size=2000)
            group_work = {g.id: g.work_id for g in objs}
            Segment.objects.bulk_create([Segment(
                id=s['id'], group_id=s['group_id'], version_id=s['version_id'], seq=s['seq'], source=s['source'],
                target=s['target'], unsplit=s.get('unsplit', False), work_id=group_work[s['group_id']],
                corpus_id=work_corpus[group_work[s['group_id']]],
            ) for s in data['segments']], batch_size=2000)
            SegmentAnnotation.objects.bulk_create([SegmentAnnotation(segment_id=s['id'], value_id=v)
                                                   for s in data['segments'] for v in s['annotations']],
                                                  batch_size=5000)
            self.stdout.write('building search index…')
            fts.rebuild()
        counts = {m.__name__: m.objects.count() for m in (Corpus, Version, Work, Paragraph, AlignGroup, Segment,
                                                          AnnotationGroup, AnnotationValue, SegmentAnnotation)}
        self.stdout.write(self.style.SUCCESS(f'loaded: {counts}'))

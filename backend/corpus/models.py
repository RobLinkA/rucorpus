"""Parallel translation corpus.

Corpus ─┬─ Version (source text + each translation, corpus-wide)
        ├─ AnnotationGroup ── AnnotationValue        (two flat levels, owned by one corpus)
        └─ Work ── Paragraph ── AlignGroup ── Segment ── annotations (M2M AnnotationValue)

A Segment is one translation's sentence pair: the source span *as that translator segmented it*
plus its translation. Translators segment differently, so an AlignGroup is the smallest source
span on which all translations of a paragraph agree; it holds ≥1 segment per translation.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', '管理员'
        EDITOR = 'editor', '标注员'
        USER = 'user', '普通用户'

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.USER)
    display_name = models.CharField(max_length=100, blank=True, default='')
    institution = models.CharField(max_length=200, blank=True, default='')

    @property
    def is_admin(self):
        return self.is_active and (self.role == self.Role.ADMIN or self.is_superuser)

    @property
    def can_edit(self):
        return self.is_active and (self.is_admin or self.role == self.Role.EDITOR)


class Corpus(models.Model):
    class Status(models.TextChoices):
        PUBLISHED = 'published', '已发布'
        HIDDEN = 'hidden', '已下架'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    source_lang = models.CharField(max_length=10, default='ru')
    target_lang = models.CharField(max_length=10, default='zh')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PUBLISHED)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'id']


class Version(models.Model):
    class Kind(models.TextChoices):
        SOURCE = 'source', '原文'
        TRANSLATION = 'translation', '译文'

    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, related_name='versions')
    kind = models.CharField(max_length=16, choices=Kind.choices)
    lang = models.CharField(max_length=10)
    label = models.CharField(max_length=200)                       # display label for this edition
    person = models.CharField(max_length=200, blank=True, default='')       # author / translator
    bibliography = models.CharField(max_length=1000, blank=True, default='')
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']


class Work(models.Model):
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, related_name='works')
    title_source = models.CharField(max_length=500)
    title_target = models.CharField(max_length=500, blank=True, default='')
    author = models.CharField(max_length=200, blank=True, default='')
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']


class Paragraph(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='paragraphs')
    seq = models.IntegerField()

    class Meta:
        ordering = ['work_id', 'seq']
        constraints = [models.UniqueConstraint(fields=['work', 'seq'], name='uniq_paragraph_seq')]


class AlignGroup(models.Model):
    paragraph = models.ForeignKey(Paragraph, on_delete=models.CASCADE, related_name='groups')
    seq = models.IntegerField()
    # denormalized for filtering / ordering without joins
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='+')
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, related_name='+')
    position = models.IntegerField(db_index=True, help_text='global reading order within the work')

    class Meta:
        ordering = ['work_id', 'position']
        constraints = [models.UniqueConstraint(fields=['paragraph', 'seq'], name='uniq_group_seq')]
        indexes = [models.Index(fields=['work', 'position'])]


class AnnotationGroup(models.Model):
    class Widget(models.TextChoices):
        CHECKBOX = 'checkbox', '复选框'
        RADIO = 'radio', '单选'
        SELECT = 'select', '下拉单选'
        MULTISELECT = 'multiselect', '下拉多选'

    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, related_name='annotation_groups')
    key = models.CharField(max_length=100, blank=True, default='')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True, default='')
    widget = models.CharField(max_length=16, choices=Widget.choices, default=Widget.CHECKBOX)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']
        constraints = [models.UniqueConstraint(fields=['corpus', 'name'], name='uniq_group_name')]

    @property
    def single_choice(self):
        return self.widget in (self.Widget.RADIO, self.Widget.SELECT)


class AnnotationValue(models.Model):
    group = models.ForeignKey(AnnotationGroup, on_delete=models.CASCADE, related_name='values')
    label = models.CharField(max_length=200)
    sort_order = models.IntegerField(default=0)
    defined_in_legacy = models.BooleanField(default=True, help_text='false: only appeared in legacy data')

    class Meta:
        ordering = ['sort_order', 'id']
        constraints = [models.UniqueConstraint(fields=['group', 'label'], name='uniq_value_label')]


class Segment(models.Model):
    group = models.ForeignKey(AlignGroup, on_delete=models.CASCADE, related_name='segments')
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name='segments')
    seq = models.IntegerField(help_text='order within paragraph for this version')
    source = models.TextField()
    target = models.TextField(blank=True, default='')
    unsplit = models.BooleanField(default=False, help_text='whole paragraph never split into sentences')
    annotations = models.ManyToManyField(AnnotationValue, through='SegmentAnnotation', through_fields=('segment', 'value'),
                                         related_name='segments')
    # denormalized
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='+')
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group_id', 'version__sort_order', 'seq']
        indexes = [models.Index(fields=['corpus', 'version']), models.Index(fields=['work'])]


class SegmentAnnotation(models.Model):
    class Origin(models.TextChoices):
        HUMAN = 'human', '人工'
        AI = 'ai', 'AI'

    segment = models.ForeignKey(Segment, on_delete=models.CASCADE)
    value = models.ForeignKey(AnnotationValue, on_delete=models.CASCADE)
    origin = models.CharField(max_length=8, choices=Origin.choices, default=Origin.HUMAN, db_index=True)
    method = models.CharField(max_length=40, blank=True, default='', help_text='AI annotator that produced it')
    evidence = models.CharField(max_length=300, blank=True, default='', help_text='words the AI annotation rests on')
    confidence = models.CharField(max_length=8, blank=True, default='')
    replaced = models.ForeignKey(AnnotationValue, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
                                 help_text='human value this AI annotation corrected')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['segment', 'value'], name='uniq_segment_value')]
        indexes = [models.Index(fields=['value', 'segment'])]


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    group = models.ForeignKey(AlignGroup, on_delete=models.CASCADE, related_name='favorites')
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['user', 'group'], name='uniq_favorite')]


class SearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='searches')
    params = models.JSONField()
    summary = models.CharField(max_length=500, blank=True, default='')
    result_count = models.IntegerField(default=0)
    name = models.CharField(max_length=200, blank=True, default='')
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pinned', '-created_at']


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)
    target = models.CharField(max_length=100, blank=True, default='')
    summary = models.CharField(max_length=500, blank=True, default='')
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ImportJob(models.Model):
    class Status(models.TextChoices):
        PREVIEW = 'preview', '待确认'
        DONE = 'done', '已导入'
        FAILED = 'failed', '失败'
        CANCELLED = 'cancelled', '已取消'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=30)
    filename = models.CharField(max_length=300)
    file = models.FileField(upload_to='imports/')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PREVIEW)
    preview = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

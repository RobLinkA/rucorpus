# Data model and integration boundaries

The [full field dictionary and AI guide](../DATA_ANNOTATION_GUIDE.md) is currently in Chinese. This English overview explains the contract for a new language or dataset. No real texts or annotations are distributed here.

## Entities

```text
Corpus ─┬─ Version
        ├─ AnnotationGroup ─ AnnotationValue
        └─ Work ─ Paragraph ─ AlignGroup ─ Segment ─ SegmentAnnotation
                                            │          │
                                            └─ Version └─ AnnotationValue
```

| Entity | Important fields and meaning |
| --- | --- |
| `Corpus` | `name`, `description`, `source_lang`, `target_lang`, `status`, `sort_order`. Owns its works, editions and annotation scheme. |
| `Version` | `corpus_id`, `kind` (`source`/`translation`), `lang`, `label`, `person`, `bibliography`, `sort_order`. Editions belong to the corpus, not directly to a work. `person` is an author/translator string, not a foreign key. |
| `Work` | `corpus_id`, `title_source`, `title_target`, `author`, `sort_order`. One literary work shared by its translations. |
| `Paragraph` | `work_id`, `seq`. Shared paragraph container; `seq` is zero-based and unique within a work. |
| `AlignGroup` | `paragraph_id`, `seq`, `work_id`, `corpus_id`, `position`. A shared source span with corresponding translation records. `position` is the work-wide reading order. |
| `Segment` | `group_id`, `version_id`, `seq`, `source`, `target`, `unsplit`, `work_id`, `corpus_id`. One edition's aligned pair; may contain several linguistic sentences. Its sequence is per version within the paragraph. |
| `AnnotationGroup` | `corpus_id`, `key`, `name`, `description`, `widget`, `sort_order`. Configurable category with checkbox/radio/select/multiselect behavior. |
| `AnnotationValue` | `group_id`, `label`, `sort_order`, `defined_in_legacy`. A label in the category. The legacy boolean is retained for schema compatibility. |
| `SegmentAnnotation` | `segment_id`, `value_id`, `origin` (`human`/`ai`), `method`, `evidence`, `confidence`, `replaced_id`. Unique pair of segment and value. `replaced_id` records a previous human value when a built-in rule corrects it. |

`Segment.source` and `.target` determine text sides; the language codes determine which NLP algorithm can run. Source is not always Russian. An annotation is attached to a segment, not automatically to every record in its alignment group. A source edition commonly holds bibliographic metadata; source strings are repeated in each translation segment. There is no separate source-sentence table, token/span annotation table, explicit work-edition join table, author table or multi-source-edition link.

Foreign-key ownership across a corpus must remain consistent. Matching numeric IDs alone is insufficient: a label and version must belong to the segment's corpus. ORM bulk operations do not automatically validate all these semantic rules.

## Exchange formats

**Canonical JSON initialization:** `manage.py load_corpus PATH` reads seven arrays: `corpora`, `versions`, `annotation_groups` (with nested `values`), `works`, `paragraphs`, `groups`, `segments`. Records use explicit numeric IDs; sequences start at zero. Segment `annotations` is an array of value IDs and is imported as human annotations. The loader derives redundant work/corpus IDs and work-wide group positions. This format does not carry full AI provenance. It initializes an empty database; `--replace` destroys the existing corpus graph and related favorites.

**Workbook/CSV:** `backend/corpus/transfer.py` defines the authoritative Chinese headers. XLSX metadata sheets are `语料库`, `版本`, `作品`, `标注体系`; the pair sheet is `句对`. Its fixed headers are `句对ID`, `作品`, `段落`, `句组`, `版本`, `句序`, `原文`, `译文`, followed by one column per annotation group. Paragraph, group and pair sequences in spreadsheets are **one-based**. Annotation cells use labels separated by semicolons. Full corpus import creates records and regenerates IDs; annotation import matches `句对ID`. Use the admin template/export endpoint to obtain headers rather than guessing them.

Upload/preview creates an import job without modifying the corpus. Confirm the preview before committing. Corpus import rejects files with errors; annotation import applies valid rows and skips erroneous ones. A successful HTTP response is not proof that every input row was imported. Spreadsheet round trips preserve unchanged existing AI rows; they do not provide an arbitrary AI-results importer with span, method and confidence fields.

For external AI results, implement a deliberate ORM/import adapter that writes `origin='ai'`, an independent `method` namespace, evidence and confidence, and preserves human decisions. The suggested JSONL staging formats in the full guide are **proposed contracts**, not accepted upload formats. Keep external batch IDs, text hashes and evidence spans in your pipeline or add a schema migration; those fields do not all exist in the database today.

## Segmentation and alignment

Preserve the original text, provenance and processing history. Detect paragraphs, then sentences, using language-specific rules for abbreviations, dialogue, punctuation and OCR. Maintain stable IDs and zero-based Unicode code-point spans `[start, end)` in an external staging representation. Never substitute model-generated paraphrases for source text.

Align paragraphs first, then source/translation spans separately for each edition. Allow 1:N and N:1 pairs. `corpus.alignment.compute_groups()` intersects shared source boundaries of already corresponding paragraphs; it does not infer semantic translation alignments or create translations. Different editions can place different numbers of segments in the same alignment group. Verify coverage and ordering before importing.

If only an original text is supplied, produce source segmentation and source-side annotations first. Do not invent a translation or label translation-dependent categories as negative; record them as inapplicable. The current parallel reading model may require a later adapter or schema extension for a standalone source-only corpus.

## Language extensions

`text.py` handles Unicode surface tokens and Russian candidate lemmas. Latin-script search preserves accents, folds case, normalizes accents to NFC and treats curly/straight apostrophes equivalently. Russian `ё` is folded to `е`. Indexing is separate from research annotation: candidate lemmas in FTS are not a disambiguated morphological gold standard.

The built-in AI runner recognizes specific Chinese group/value names. Creating arbitrary categories does not create detectors. Its Russian algorithms use pymorphy3/Natasha; its Chinese algorithms use rules/jieba and an optional user-supplied lexicon. English, French and Spanish morphology or automatic labeling require their own models, tests and method namespace. Built-in reruns refresh only built-in methods, optionally scoped by `--corpus ID`, and retain external method results.

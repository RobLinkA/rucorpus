# RuCorpus

**A Russian-first parallel corpus search and annotation system. Bring your own data.**

RuCorpus provides multi-translation alignment, Russian morphological search, parallel reading, configurable sentence-pair annotations and corpus administration. This repository distributes the reusable software under the [MIT license](LICENSE). It contains **no research corpus, real annotation records, user database, credentials, private keys or production backups**. Database migrations create an empty schema. Tests and documentation use small invented examples only.

[中文说明](docs/README.zh-CN.md) · [English data model](docs/DATA_MODEL.md) · [数据与 AI 标注指南](DATA_ANNOTATION_GUIDE.md) · [Deployment and recovery](docs/DEPLOYMENT.md)

## Language support

| Language | Word, phrase and prefix search | Morphological matching | Built-in annotation algorithms |
| --- | --- | --- | --- |
| Russian | Yes; case-insensitive, `ё`/`е` folded | pymorphy3 dictionary analyses | Russian morphology and selected Natasha syntax rules |
| English | Yes; case-insensitive | No stemming or lemmatization | None |
| French / Spanish | Yes; accented letters, composed/decomposed accents and straight/curly apostrophes | No stemming or lemmatization | None |
| Chinese | Literal substring search | Not applicable | Limited jieba and structural rules; optional user-supplied idiom lexicon |

English works for the core corpus structure, import/export, reading and basic search. Searching `walk` does **not** automatically match `walked` or `walking`; `walk*` is a prefix query. French and Spanish accents are significant: `café` differs from `cafe`. Phrase/prefix queries match surface forms, even in Russian morphological mode. The current interface and spreadsheet headers are Chinese; a translated interface is not included. Language codes are editable (`ru`, `zh`, `en`, `fr`, `es`, etc.), but a language code alone does not add NLP support.

## Features

- Search either side of sentence pairs; combine corpus, work, version and annotation filters; highlight and export results.
- Read aligned translations by sentence group or paragraph, show annotations, navigate with arrow keys.
- Define each corpus's own annotation groups and values; edit, split and annotate sentence pairs.
- Preview and commit XLSX/CSV imports, export workbooks, track edits in an audit log.
- Administrator/editor/reader roles, session authentication, CSRF protection, personal favorites and history.
- Optional rule-based annotation with method, evidence, confidence and human-correction provenance. Built-in reruns preserve external methods and support `--corpus ID`.
- Responsive Vue interface with light/dark themes and configurable branding.

## Quick start

Requires Python 3.12 and Node.js **22.12+**, with SQLite FTS5 available. No dataset download is needed.

```sh
git clone https://github.com/RobLinkA/rucorpus.git
cd rucorpus/backend
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python manage.py migrate
python manage.py create_admins administrator
python manage.py runserver 127.0.0.1:8000
```

The administrator command prompts for your password; no account or default password is shipped. In a second terminal:

```sh
cd rucorpus/frontend
npm ci
npm run dev
```

Open <http://localhost:5173>. Log in, create a corpus in the administration area and import **your own** aligned texts. `migrate` leaves all corpus and annotation tables empty.

For a canonical JSON initialization, prepare the seven-array structure documented in [DATA_ANNOTATION_GUIDE.md](DATA_ANNOTATION_GUIDE.md), then run:

```sh
python manage.py load_corpus /absolute/path/to/your-corpus.json
python manage.py rebuild_index
```

The JSON loader initializes a database; it does not append to an existing corpus. `--replace` deletes all existing corpora and their dependent records, including favorites. Spreadsheet imports and canonical JSON have different capabilities; neither is a full AI-provenance interchange format. See the guide before building an automation pipeline.

## Optional annotation

```sh
python manage.py ai_annotate --corpus 1
```

Rules run only when their expected group/value names exist; they do not infer an arbitrary research scheme. The guide documents these names and limitations. No third-party wordlist or annotation result is bundled. Set `RUCORPUS_IDIOMS_PATH` to an authorized local UTF-8 idiom list if needed; without it, Chinese four-character detection uses structural rules with reduced coverage. Built-in algorithms can replace specific conflicting human labels and record the previous value; inspect their rules and back up your own database before running.

## Development

```sh
cd backend
python -m pytest
python manage.py makemigrations --check --dry-run
# In frontend:
npm run build
```

Tests generate disposable synthetic records, verify multilingual search/highlighting, roles and CSRF, annotation provenance, spreadsheet round trips and initialization from an empty database. They never read a research dataset.

```text
backend/corpus/models.py       Data model and constraints
backend/corpus/text.py         Unicode tokenization, Russian lemmas, highlighting
backend/corpus/search.py       Search filters and SQLite FTS queries
backend/corpus/alignment.py    Shared source boundaries for pre-aligned paragraphs
backend/corpus/transfer.py     XLSX/CSV exchange and preview/commit plans
backend/corpus/ai/             Optional language-specific annotation rules
backend/corpus/api/            Public, user and administration APIs
frontend/src/                 Vue interface
docs/                         Setup, deployment, contribution and data boundaries
```

Legacy database extraction, source-text repair scripts and dataset-specific migrations are intentionally excluded. There is no automatic translator, general paragraph aligner or arbitrary raw-text-to-corpus importer; data preparation must supply aligned sentence pairs. API documentation is available at `/api/docs`.

## Deploying

Use the included [Docker Compose configuration](compose.yaml) or the [native deployment guide](docs/DEPLOYMENT.md). Both start empty and use separate persistent storage. The guide covers HTTPS, backups and recovery. Publishing this repository does not host a running database-backed website on GitHub Pages.

## License and data rights

RuCorpus code and documentation are MIT-licensed. Imported texts, translations, annotations and optional resources remain subject to their own rights and licenses; the software license grants no rights to a separate corpus. Dependencies retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). Contributions should contain code and invented tests only: [CONTRIBUTING.md](CONTRIBUTING.md).

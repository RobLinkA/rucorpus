# Contributing

Open an issue for a proposed data-model or language-processing change. Keep changes focused and document whether a capability is implemented, experimental or a proposed interchange format.

Never commit real corpus excerpts, annotation exports, user records, SQLite/SQL files, optional wordlists, private keys, `.env` files or backups. Use short invented test strings. Tests create their records at runtime; no dataset should be required to run CI.

Before submitting, run backend pytest, `manage.py makemigrations --check --dry-run`, and the frontend build. Add meaningful tests when changing matching, alignment, import semantics, permissions or AI replacement behavior. Changing tokenization requires rebuilding existing installations' FTS indexes with `manage.py rebuild_index`.

Preserve foreign-key ownership and the distinction between a sentence pair and a linguistic sentence. See [DATA_ANNOTATION_GUIDE.md](DATA_ANNOTATION_GUIDE.md). External AI annotators must use their own method namespace; do not reuse built-in method names or delete another algorithm's records.

By contributing, you agree to license your contribution under this repository's MIT license. Retain notices for any third-party code.

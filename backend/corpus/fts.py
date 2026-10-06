"""SQLite FTS5 index over segments.

segment_fts(rowid = segment.id): folded surface tokens and lemma tokens of both sides.
Word-based languages (Russian, Latin script) are matched here; CJK text is matched with instr()
directly on the segment table (character-level substring search is exact and fast at this size).
"""
from django.db import connection

from .text import lemma_tokens, surface_tokens

CREATE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS segment_fts USING fts5(
    src_surface, src_lemmas, tgt_surface, tgt_lemmas,
    tokenize = "unicode61 remove_diacritics 0 tokenchars '_'"
)
"""
DROP_SQL = 'DROP TABLE IF EXISTS segment_fts'


def _row(seg_id, source, target):
    return (seg_id, surface_tokens(source), lemma_tokens(source), surface_tokens(target), lemma_tokens(target))


def index_segments(rows, cursor=None):
    """rows: iterable of (id, source, target)."""
    cur = cursor or connection.cursor()
    data = [_row(*r) for r in rows]
    cur.executemany('DELETE FROM segment_fts WHERE rowid = %s', [(d[0],) for d in data])
    cur.executemany('INSERT INTO segment_fts(rowid, src_surface, src_lemmas, tgt_surface, tgt_lemmas) '
                    'VALUES (%s, %s, %s, %s, %s)', data)


def remove_segments(ids):
    with connection.cursor() as cur:
        cur.executemany('DELETE FROM segment_fts WHERE rowid = %s', [(i,) for i in ids])


def rebuild():
    from .models import Segment
    with connection.cursor() as cur:
        cur.execute(DROP_SQL)
        cur.execute(CREATE_SQL)
        batch = []
        for row in Segment.objects.values_list('id', 'source', 'target').iterator(chunk_size=2000):
            batch.append(row)
            if len(batch) >= 2000:
                index_segments(batch, cur)
                batch = []
        if batch:
            index_segments(batch, cur)
        cur.execute("INSERT INTO segment_fts(segment_fts) VALUES ('optimize')")

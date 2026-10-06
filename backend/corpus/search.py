"""Corpus search: keyword (morphological / exact) + scope + annotation filters → alignment groups."""
from dataclasses import dataclass, field

from django.db import connection

from .text import lemmas, parse_query, fold, surface_tokens


@dataclass
class SearchParams:
    q: str = ''
    mode: str = 'morph'                 # 'morph' | 'exact'
    corpora: list = field(default_factory=list)
    works: list = field(default_factory=list)
    versions: list = field(default_factory=list)
    values: list = field(default_factory=list)  # annotation value ids
    logic: str = 'or'                   # 'or' | 'and' | 'group' (any within a group, all across groups)
    exclude: list = field(default_factory=list)  # annotation value ids that must be absent
    origin: str = 'all'                 # 'all' | 'human' | 'ai' — which annotations the filters look at
    include_hidden: bool = False


class QueryError(ValueError):
    pass


def _fts_expr(term, mode):
    text = term['text']
    if term['phrase'] and ' ' in text.strip():
        words = surface_tokens(text).split()
        return '{src_surface tgt_surface} : "' + ' '.join(w.replace('"', '') for w in words) + '"'
    if text.endswith('*') and len(text) > 2:
        return '{src_surface tgt_surface} : "' + fold(text[:-1]).replace('"', '') + '"*'
    if mode == 'morph' and term['script'] == 'ru' and not term['phrase']:
        ls = [lm.replace('-', '_').replace('"', '') for lm in lemmas(text)]
        return '{src_lemmas tgt_lemmas} : (' + ' OR '.join(f'"{lm}"' for lm in ls) + ')'
    return '{src_surface tgt_surface} : "' + fold(text).replace('-', '_').replace('"', '') + '"'


def build_where(p: SearchParams):
    """Return (sql_conditions, params) over alias s (corpus_segment) / c (corpus_corpus)."""
    where, args = [], []
    if not p.include_hidden:
        where.append("c.status = 'published'")
    terms = parse_query(p.q)
    for t in terms:
        if t['script'] == 'zh':
            where.append('(instr(s.source, %s) > 0 OR instr(s.target, %s) > 0)')
            args += [t['text'], t['text']]
        else:
            where.append('s.id IN (SELECT rowid FROM segment_fts WHERE segment_fts MATCH %s)')
            args.append(_fts_expr(t, p.mode))
    for col, ids in (('s.corpus_id', p.corpora), ('s.work_id', p.works), ('s.version_id', p.versions)):
        if ids:
            where.append(f"{col} IN ({','.join(['%s'] * len(ids))})")
            args += list(ids)
    org, org_args = ('', []) if p.origin not in ('human', 'ai') else (' AND origin = %s', [p.origin])
    sa = 'SELECT segment_id FROM corpus_segmentannotation WHERE value_id IN ({ph})' + org
    if p.values:
        ph = ','.join(['%s'] * len(p.values))
        if p.logic == 'and':
            where.append(f's.id IN ({sa.format(ph=ph)} GROUP BY segment_id HAVING COUNT(DISTINCT value_id) = %s)')
            args += list(p.values) + org_args + [len(set(p.values))]
        elif p.logic == 'group':
            from .models import AnnotationValue
            by_group = {}
            for vid, gid in AnnotationValue.objects.filter(id__in=p.values).values_list('id', 'group_id'):
                by_group.setdefault(gid, []).append(vid)
            for ids in by_group.values():
                where.append(f"s.id IN ({sa.format(ph=','.join(['%s'] * len(ids)))})")
                args += ids + org_args
        else:
            where.append(f's.id IN ({sa.format(ph=ph)})')
            args += list(p.values) + org_args
    elif p.origin in ('human', 'ai'):
        where.append('s.id IN (SELECT segment_id FROM corpus_segmentannotation WHERE origin = %s)')
        args.append(p.origin)
    if p.exclude:
        ph = ','.join(['%s'] * len(p.exclude))
        where.append(f's.id NOT IN ({sa.format(ph=ph)})')
        args += list(p.exclude) + org_args
    return (' AND '.join(where) or '1=1'), args, terms


def search(p: SearchParams, page=1, page_size=20, with_facets=True):
    if not parse_query(p.q) and not p.values and not p.works and not p.versions and not p.corpora \
            and p.origin not in ('human', 'ai'):
        raise QueryError('请输入关键词或选择筛选条件')
    where, args, terms = build_where(p)
    base = f'''FROM corpus_segment s JOIN corpus_corpus c ON c.id = s.corpus_id WHERE {where}'''
    with connection.cursor() as cur:
        cur.execute(f'''
            CREATE TEMP TABLE IF NOT EXISTS _hits(id INTEGER PRIMARY KEY, group_id INTEGER, version_id INTEGER,
                                                  work_id INTEGER, corpus_id INTEGER)''')
        cur.execute('DELETE FROM _hits')
        cur.execute(f'INSERT INTO _hits SELECT s.id, s.group_id, s.version_id, s.work_id, s.corpus_id {base}', args)
        cur.execute('SELECT COUNT(*), COUNT(DISTINCT group_id) FROM _hits')
        n_segments, n_groups = cur.fetchone()
        offset = (max(page, 1) - 1) * page_size
        cur.execute('''
            SELECT g.id FROM corpus_aligngroup g
              JOIN corpus_work w ON w.id = g.work_id JOIN corpus_corpus c ON c.id = g.corpus_id
             WHERE g.id IN (SELECT group_id FROM _hits)
             ORDER BY c.sort_order, c.id, w.sort_order, w.id, g.position
             LIMIT %s OFFSET %s''', [page_size, offset])
        group_ids = [r[0] for r in cur.fetchall()]
        ph = ','.join(['%s'] * len(group_ids)) or 'NULL'
        cur.execute(f'SELECT id FROM _hits WHERE group_id IN ({ph})', group_ids)
        hit_segments = {r[0] for r in cur.fetchall()}
        facets = {}
        if with_facets:
            for key, col in (('corpora', 'corpus_id'), ('works', 'work_id'), ('versions', 'version_id')):
                cur.execute(f'SELECT {col}, COUNT(DISTINCT group_id) FROM _hits GROUP BY {col}')
                facets[key] = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute('''SELECT sa.value_id, COUNT(*) FROM corpus_segmentannotation sa
                           JOIN _hits h ON h.id = sa.segment_id GROUP BY sa.value_id''')
            facets['values'] = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute('DELETE FROM _hits')
    return {
        'total_groups': n_groups, 'total_segments': n_segments,
        'group_ids': group_ids, 'hit_segments': hit_segments, 'terms': terms, 'facets': facets,
    }


def all_group_ids(p: SearchParams, limit=20000):
    """Every matching group id in reading order (used for export)."""
    where, args, terms = build_where(p)
    with connection.cursor() as cur:
        cur.execute(f'''
            SELECT g.id, GROUP_CONCAT(s.id) FROM corpus_segment s
              JOIN corpus_corpus c ON c.id = s.corpus_id
              JOIN corpus_aligngroup g ON g.id = s.group_id JOIN corpus_work w ON w.id = g.work_id
             WHERE {where}
             GROUP BY g.id ORDER BY c.sort_order, c.id, w.sort_order, w.id, g.position LIMIT %s''',
                    args + [limit])
        rows = cur.fetchall()
    hits = {int(x) for _, ids in rows for x in ids.split(',')}
    return [r[0] for r in rows], hits, terms

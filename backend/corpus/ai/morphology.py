"""Rule-based Russian morphology annotators (pymorphy3, dictionary words only).

Each detector returns {value_label: [evidence words]} for one Russian text.
"""
import functools
import re

from ..text import morph

WORD_RE = re.compile(r'[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*')

ANSWER_NET = re.compile(r'(?:^|[«"—–\-:.!?]\s*)нет\s*[,.!?…]', re.I)  # "Нет, …" answer particle


@functools.lru_cache(maxsize=100_000)
def best_known_parse(word):
    """Highest-scoring dictionary parse of the lower-cased word, or None for unknown words
    (unknown words are mostly names/transliterations: Ефимыча, Цзюе-синь…)."""
    parses = [p for p in morph().parse(word.lower()) if p.is_known]
    return max(parses, key=lambda p: p.score) if parses else None


def noun_homograph(word):
    """'пристав', 'управляющий': forms that are (also) ordinary nouns are not counted as verb forms."""
    return any('NOUN' in q.tag and q.is_known and q.score >= 0.25 for q in morph().parse(word.lower()))


def words(text):
    for m in WORD_RE.finditer(text or ''):
        p = best_known_parse(m.group())
        if p is not None and not ({'GRND', 'PRTF', 'PRTS'} & p.tag.grammemes and noun_homograph(m.group())):
            yield m.group(), p


def tokens(text):
    """[(word, best known parse or None, start offset)] for every word."""
    return [(m.group(), best_known_parse(m.group()), m.start()) for m in WORD_RE.finditer(text or '')]


def is_verbal(p):
    return p is not None and ('VERB' in p.tag or 'INFN' in p.tag)


def predicative(toks, i, text):
    """PRED words used predicatively: existential 'нет' (not the answer particle 'Нет, …'),
    and adverb-like predicatives ('плохо', 'хорошо') only when no verb sits next to them."""
    w, p, start = toks[i]
    lw = w.lower()
    if lw == 'нет':
        return not ANSWER_NET.match(text[max(0, start - 3):start + 5].lstrip()) and not ANSWER_NET.search(text[max(0, start - 3):start + 5])
    if p is None or 'PRED' not in p.tag:
        return False
    if any('ADVB' in q.tag for q in morph().parse(lw)):
        neighbours = [toks[j][1] for j in (i - 1, i + 1) if 0 <= j < len(toks)]
        if any(is_verbal(q) for q in neighbours):
            return False
    return True


def aspect(tag):
    return '完成体' if 'perf' in tag else '未完成体'


def nonfinite_forms(text):
    """非变位形式: 主动形动词 / 被动形动词 / 副动词 / 命令式."""
    out = {}
    for w, p in words(text):
        t = p.tag
        if 'GRND' in t:
            out.setdefault('副动词', []).append(w)
        elif 'PRTF' in t or 'PRTS' in t:
            out.setdefault('主动形动词' if 'actv' in t else '被动形动词', []).append(w)
        elif 'VERB' in t and 'impr' in t:
            out.setdefault('命令式', []).append(w)
    return out


def verbal_forms(text):
    """Ba Jin scheme: 述谓词 / 副动词(体) / 主动形动词(体) / 被动形动词(体·长短尾). Returns {(group, value): words}."""
    out = {}
    toks = tokens(text)
    for i, (w, p, _) in enumerate(toks):
        if predicative(toks, i, text):
            out.setdefault(('述谓词', '述谓词'), []).append(w)
            continue
        if p is None or ({'GRND', 'PRTF', 'PRTS'} & p.tag.grammemes and noun_homograph(w)):
            continue
        t = p.tag
        if 'GRND' in t:
            out.setdefault(('副动词', f'{aspect(t)}副动词'), []).append(w)
        elif 'PRTF' in t or 'PRTS' in t:
            if 'actv' in t:
                out.setdefault(('主动形动词', f'{aspect(t)}主动形动词'), []).append(w)
            else:
                tail = '长尾' if 'PRTF' in t else '短尾'
                out.setdefault(('被动形动词', f'{aspect(t)}被动形动词{tail}'), []).append(w)
    return out

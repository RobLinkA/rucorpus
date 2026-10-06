"""Language helpers: tokenizing, Russian lemmatization (pymorphy3), query parsing, highlighting."""
import functools
import re
import threading
import unicodedata

WORD = r"[^\W_]+(?:[\u0300-\u036f]+[^\W_]*)*"
WORD_RE = re.compile(WORD + r"(?:[-'’]" + WORD + r")*")
CYR_RE = re.compile(r'[А-Яа-яЁё]')
CJK_RE = re.compile(r'[㐀-鿿]')

_morph = None
_morph_lock = threading.Lock()


def morph():
    global _morph
    if _morph is None:
        with _morph_lock:
            if _morph is None:
                import pymorphy3
                _morph = pymorphy3.MorphAnalyzer(lang='ru')
    return _morph


def fold(word):
    return unicodedata.normalize('NFC', word).lower().replace('ё', 'е').replace('’', "'")


@functools.lru_cache(maxsize=200_000)
def lemmas(word):
    """All dictionary forms a Russian word form may belong to (folded)."""
    w = fold(word)
    if not CYR_RE.search(w):
        return (w,)
    parts = w.split('-')
    if len(parts) > 1 and all(parts):
        # hyphenated: lemmatize as a whole when known, else by parts
        known = {fold(p.normal_form) for p in morph().parse(w) if p.is_known}
        if known:
            return tuple(sorted(known))
    return tuple(sorted({fold(p.normal_form) for p in morph().parse(w)}))


def lemma_tokens(text):
    """Space-separated lemma string for the FTS index. Lemmas are joined with '_' inside a word
    so FTS treats each as a token: 'стали' -> 'сталь стать'."""
    out = []
    for m in WORD_RE.finditer(text or ''):
        for lm in lemmas(m.group()):
            out.append(lm.replace('-', '_'))
    return ' '.join(out)


def surface_tokens(text):
    return ' '.join(fold(m.group()).replace('-', '_') for m in WORD_RE.finditer(text or ''))


def script_of(term):
    if CJK_RE.search(term):
        return 'zh'
    if CYR_RE.search(term):
        return 'ru'
    return 'latin'


def parse_query(q):
    """Split a query into terms. "quoted text" is a phrase. Returns [{'text','phrase','script'}]."""
    terms = []
    for m in re.finditer(r'"([^"]+)"|“([^”]+)”|«([^»]+)»|(\S+)', q or ''):
        text = next(g for g in m.groups() if g is not None).strip()
        phrase = m.group(4) is None
        if not text:
            continue
        terms.append({'text': text, 'phrase': phrase or (script_of(text) == 'zh'), 'script': script_of(text)})
    return terms


class Highlighter:
    """Compute [start, end] spans to highlight for a set of parsed terms."""

    def __init__(self, terms, mode):
        self.mode = mode
        self.substrings = []        # CJK / phrases / exact latin: literal (case-insensitive) matches
        self.lemma_sets = []        # morph mode Russian words
        self.words = set()          # exact mode single words
        for t in terms:
            if t['script'] == 'zh' or t['phrase'] and ' ' in t['text']:
                self.substrings.append(t['text'])
            elif t['script'] == 'ru' and mode == 'morph' and not t['text'].endswith('*'):
                self.lemma_sets.append(set(lemmas(t['text'])))
            elif t['text'].endswith('*'):
                self.substrings.append(t['text'].rstrip('*'))
            else:
                self.words.add(fold(t['text']))

    def spans(self, text):
        if not text:
            return []
        spans = []
        # Preserve original offsets even for decomposed accents or expanding lowercase.
        chunks = list(re.finditer(r'.[\u0300-\u036f]*', text, re.S))
        folded = [fold(m.group()) for m in chunks]
        low = ''.join(folded)
        offsets = [(m.start(), m.end()) for m, part in zip(chunks, folded) for _ in part]
        for s in self.substrings:
            needle = fold(s)
            start = 0
            while needle and (i := low.find(needle, start)) >= 0:
                spans.append([offsets[i][0], offsets[i + len(needle) - 1][1]])
                start = i + len(needle)
        if self.lemma_sets or self.words:
            all_lemmas = set().union(*self.lemma_sets) if self.lemma_sets else set()
            for m in WORD_RE.finditer(text):
                w = fold(m.group())
                if w in self.words or (all_lemmas and all_lemmas.intersection(lemmas(m.group()))):
                    spans.append([m.start(), m.end()])
        spans.sort()
        merged = []
        for s in spans:
            if merged and s[0] <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], s[1])
            else:
                merged.append(s)
        return merged

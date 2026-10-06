"""单部句类型 (one-member sentence types) from a dependency parse (Natasha / slovnet).

A clause head is the root or a coordinated / paratactic predicate. A clause without a subject is
classified by the form of its head. Only types that the evaluation showed to be reliable are used.
"""
import functools

from ..text import morph

SUBJ = {'nsubj', 'nsubj:pass', 'csubj', 'csubj:pass', 'expl'}
HEAD_RELS = {'root', 'conj', 'parataxis'}


@functools.lru_cache(maxsize=1)
def _pipeline():
    from natasha import Doc, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, Segmenter
    emb = NewsEmbedding()
    return Doc, Segmenter(), NewsMorphTagger(emb), NewsSyntaxParser(emb)


def parse(text):
    Doc, seg, morph_tagger, syntax = _pipeline()
    # sentence-initial capitals confuse the tagger (Помолчав → PROPN): lower-case the first letter
    doc = Doc(text[:1].lower() + text[1:] if text else text)
    doc.segment(seg)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax)
    return doc


def is_predicative(word):
    return any('PRED' in p.tag and p.is_known for p in morph().parse(word.lower()))


def classify(text):
    """{type: [head words]} for subjectless clauses."""
    out = {}
    doc = parse(text)
    for sent in doc.sents:
        toks = sent.tokens
        children = {}
        for t in toks:
            children.setdefault(t.head_id, []).append(t)
        by_id = {t.id: t for t in toks}

        def has_subject(t):
            # coordinated predicates share the subject of the predicate they are attached to
            seen = set()
            while t is not None and t.id not in seen:
                seen.add(t.id)
                if any(k.rel in SUBJ for k in children.get(t.id, [])):
                    return True
                if t.rel not in ('conj', 'parataxis'):
                    return False
                t = by_id.get(t.head_id)
            return False

        def agreeing_nominative(h):
            f = h.feats
            for t in toks:
                if t is h or t.feats.get('Case') != 'Nom' or t.pos not in ('NOUN', 'PRON', 'PROPN'):
                    continue
                if f.get('Number') and t.feats.get('Number') and t.feats['Number'] != f['Number']:
                    continue
                if f.get('Person') in ('1', '2') and t.feats.get('Person') != f['Person']:
                    continue
                return True
            return False

        for h in toks:
            if h.rel not in HEAD_RELS:
                continue
            if h.rel != 'root' and h.pos not in ('VERB', 'ADV', 'ADJ'):
                continue
            kids = children.get(h.id, [])
            if has_subject(h) or (h.pos == 'VERB' and agreeing_nominative(h)):
                continue
            f = h.feats
            word = h.text.lower()
            if h.pos == 'VERB' and f.get('VerbForm') == 'Fin':
                if f.get('Mood') == 'Imp':
                    continue
                if f.get('Number') == 'Plur' and (f.get('Person') == '3' or f.get('Tense') == 'Past'):
                    no_nominative = not any(t.feats.get('Case') == 'Nom' and t.pos in ('NOUN', 'PRON', 'PROPN', 'ADJ', 'DET')
                                            for t in toks)
                    if h.rel == 'root' and no_nominative:
                        out.setdefault('不定人称句', []).append(h.text)
                elif f.get('Person') in ('1', '2') and f.get('Number') != 'Plur' or f.get('Person') == '1':
                    out.setdefault('确定人称句', []).append(h.text)
                elif f.get('Number') == 'Sing' and (f.get('Gender') == 'Neut' or f.get('Person') == '3') \
                        and not word.endswith(('ся', 'сь')):
                    out.setdefault('无人称句', []).append(h.text)
            elif h.pos == 'VERB' and f.get('VerbForm') == 'Inf' and h.rel == 'root':
                if not any(k.pos == 'VERB' and k.feats.get('VerbForm') == 'Fin' for k in kids):
                    out.setdefault('不定式句', []).append(h.text)
            elif is_predicative(word) and word not in ('нет',) or word == 'нет' and any(k.feats.get('Case') == 'Gen' for k in kids):
                out.setdefault('无人称句', []).append(h.text)
    return out

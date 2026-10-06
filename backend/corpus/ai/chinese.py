"""Rule-based annotators for Chinese translations: 叠词 / 四字格 / 象声词.

Definitions follow the corpus scheme (译文修辞). Rules are lexical/structural; word boundaries
come from jieba so that accidental repeats across words (医院|院子) are not counted.
"""
import functools
import re
from pathlib import Path
import os

C = '[一-鿿]'
# An optional locally supplied lexicon. No wordlist is distributed in this repo.
IDIOMS_PATH = os.environ.get('RUCORPUS_IDIOMS_PATH', '')

# Onomatopoeia (象声词). AA-type sound words are counted here, not as 叠词.
ONOMATOPOEIA = {
    '哈哈', '哇哇', '嘻嘻', '嘿嘿', '呵呵', '咯咯', '格格', '呜呜', '嗡嗡', '咕咕', '咕噜', '咕咚', '嘟嘟', '叮当', '叮咚',
    '丁当', '叮叮', '当当', '咚咚', '砰砰', '砰', '啪', '啪啪', '噼啪', '劈啪', '哗哗', '哗啦', '轰隆', '轰轰', '隆隆',
    '嘀嗒', '滴答', '扑通', '噗通', '扑哧', '噗嗤', '吱吱', '吱呀', '吱嘎', '嘎吱', '嘎嘎', '呱呱', '汪汪',
    '喵', '咩', '哞', '嗖', '嗖嗖', '飕飕', '呼呼', '呼哧', '沙沙', '簌簌', '潺潺', '淙淙', '哐当', '咣当', '咔嚓',
    '喀嚓', '嘶嘶', '咝咝', '叽叽喳喳', '叽叽', '喳喳', '唧唧', '嘤嘤', '哎哟', '嗷嗷', '嗬嗬', '呼噜', '咿呀',
    '嘣', '咣', '哐', '喔喔', '啾啾', '萧萧', '琅琅', '铮铮', '飒飒', '辘辘', '隆隆', '啧啧', '嚓嚓', '啷当',
}
# Lexical AA nouns (kinship, fixed words) and repeats annotators never treat as rhetoric.
NOT_REDUP = {
    '爸爸', '妈妈', '爷爷', '奶奶', '姥姥', '哥哥', '姐姐', '弟弟', '妹妹', '太太', '叔叔', '伯伯', '舅舅', '姑姑', '婶婶',
    '嫂嫂', '公公', '婆婆', '宝宝', '星星', '猩猩', '蝈蝈', '蛐蛐', '等等', '明明', '谢谢', '仅仅',
}
# Dictionary idioms that are ordinary lexicalised words in modern Chinese.
NOT_SIZIGE = {'不好意思', '总而言之', '有生以来', '诸如此类', '新陈代谢', '终身大事', '一无所知'}
FOUR_PATTERNS = [rf'不{C}不{C}', rf'{C}来{C}去', rf'无{C}无{C}', rf'一{C}一{C}', rf'千{C}万{C}', rf'有{C}有{C}',
                 rf'({C})\1({C})\2']


@functools.lru_cache(maxsize=1)
def idioms():
    if not IDIOMS_PATH:
        return set()
    lines = Path(IDIOMS_PATH).read_text(encoding='utf-8').splitlines()
    return {x.strip() for x in lines if x.strip() and not x.startswith('#')} - NOT_SIZIGE


@functools.lru_cache(maxsize=1)
def _jieba():
    import jieba
    jieba.setLogLevel(60)
    for w in ONOMATOPOEIA | idioms():
        jieba.add_word(w, freq=2000)
    return jieba


def cut(text):
    return _jieba().lcut(text or '')


def reduplication(text):
    """叠词: AA / ABB / AABB words, and verb A了A / A一A patterns."""
    found = []
    for tok in cut(text):
        if tok in NOT_REDUP or tok in ONOMATOPOEIA or tok[:2] in ONOMATOPOEIA or tok[-2:] in ONOMATOPOEIA:
            continue
        if re.fullmatch(rf'({C})\1', tok) or re.fullmatch(rf'{C}({C})\1', tok) or re.fullmatch(rf'({C})\1({C})\2', tok) \
                or re.fullmatch(rf'({C})\1{C}', tok) and tok[:2] not in NOT_REDUP:
            found.append(tok)
    for m in re.finditer(rf'({C})[了一]\1', text or ''):
        if m.group(1) not in '一了不是有':
            found.append(m.group())
    return found


def four_character(text):
    """四字格: dictionary idioms (成语) and productive four-character frames (来来去去, 不X不Y…)."""
    text = text or ''
    found = [text[i:i + 4] for i in range(len(text) - 3) if text[i:i + 4] in idioms()]
    for rx in FOUR_PATTERNS:
        found += [m.group() for m in re.finditer(rx, text) if m.group() not in found]
    return found


def onomatopoeia(text):
    return [tok for tok in cut(text) if tok in ONOMATOPOEIA]

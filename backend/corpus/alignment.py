"""Find shared boundaries for versions already aligned to the same source paragraph.

This does not infer translations or align unrelated paragraphs.
"""
import difflib


def alnum(text):
    return ''.join(ch.lower() for ch in text if ch.isalnum()).replace('ё', 'е')


def compute_groups(version_segments):
    """version_segments: {version_id: [source_text, ...]} for one paragraph.
    Returns {version_id: [group_index per segment]}."""
    if not version_segments:
        return {}
    if any(not pieces or any(not alnum(piece) for piece in pieces) for pieces in version_segments.values()):
        raise ValueError('Every version needs non-empty source pieces containing letters or numbers.')
    vids = list(version_segments)
    base_vid = vids[0]
    base = alnum(''.join(version_segments[base_vid]))
    mapped = {}
    for vid in vids:
        segs = version_segments[vid]
        own = alnum(''.join(segs))
        ends, acc = [], 0
        for s in segs:
            acc += len(alnum(s))
            ends.append(acc)
        if own == base:
            mapped[vid] = ends
            continue
        # map offsets of this version's string into base coordinates
        sm = difflib.SequenceMatcher(None, own, base, autojunk=False)
        def to_base(off):
            for a, b, size in sm.get_matching_blocks():
                if a <= off <= a + size:
                    return b + (off - a)
            # inside a non-matching region: snap to the next matching block start
            for a, b, size in sm.get_matching_blocks():
                if a >= off:
                    return b
            return len(base)
        m = [to_base(e) for e in ends]
        m[-1] = len(base)
        mapped[vid] = m
    common = set(mapped[base_vid])
    for vid in vids[1:]:
        common &= set(mapped[vid])
    common.add(len(base))
    bounds = sorted(common)
    result = {}
    for vid in vids:
        gi = []
        for e in mapped[vid]:
            # first common boundary >= this segment end
            lo = 0
            while bounds[lo] < e:
                lo += 1
            gi.append(lo)
        # empty / zero-length segments: attach to previous group
        result[vid] = gi
    # renumber groups densely
    used = sorted({g for v in result.values() for g in v})
    remap = {g: i for i, g in enumerate(used)}
    return {vid: [remap[g] for g in gs] for vid, gs in result.items()}

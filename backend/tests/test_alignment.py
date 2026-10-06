import pytest

from corpus.alignment import compute_groups


def test_shared_boundaries_keep_version_specific_splits():
    assert compute_groups({1: ['Он вошёл. Он сел.'], 2: ['Он вошёл.', 'Он сел.']}) == {
        1: [0], 2: [0, 0]}
    assert compute_groups({1: ['Он вошёл.', 'Он сел.'], 2: ['Он вошёл.', 'Он сел.']}) == {
        1: [0, 1], 2: [0, 1]}


def test_alignment_empty_input_and_invalid_pieces():
    assert compute_groups({}) == {}
    with pytest.raises(ValueError):
        compute_groups({1: []})
    with pytest.raises(ValueError):
        compute_groups({1: ['...']})

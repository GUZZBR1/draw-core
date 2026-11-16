"""Contratos de presença de mão: HandSignature e HandSample."""

from dataclasses import FrozenInstanceError

import pytest

from draw.contracts import HandSample, HandSignature


def test_hand_signature_valid_and_frozen():
    signature = HandSignature(area=500.0, centroid_x=50.0, centroid_y=60.0)
    assert signature.area == 500.0
    with pytest.raises(FrozenInstanceError):
        signature.area = 0.0


def test_hand_signature_rejects_non_finite_and_negative():
    for bad in (float("inf"), float("nan"), "muita"):
        with pytest.raises(ValueError):
            HandSignature(area=1.0, centroid_x=bad, centroid_y=0.0)
    with pytest.raises(ValueError):
        HandSignature(area=-1.0, centroid_x=0.0, centroid_y=0.0)
    zero = HandSignature(area=0.0, centroid_x=0.0, centroid_y=0.0)
    assert zero.area == 0.0  # "sem mão" de quem respondeu


def test_hand_sample_valid_and_frozen():
    for present in (True, False, None):
        sample = HandSample(present=present, moved=False)
        assert sample.present is present
    sample = HandSample(present=True, moved=True)
    assert sample.moved is True
    with pytest.raises(FrozenInstanceError):
        sample.moved = False


def test_hand_sample_rejects_bad_fields():
    with pytest.raises(ValueError):
        HandSample(present="talvez", moved=False)
    with pytest.raises(ValueError):
        HandSample(present=True, moved=1)

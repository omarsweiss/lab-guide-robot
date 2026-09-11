# Unit tests for offset.py.

import math

import pytest

from lab_guide_perception.offset import BoundingBox, bearing, largest, normalized_offset, yaw_error

WIDTH = 640
HFOV = math.radians(80.0)


def box_at(center_x: float, width: float = 40.0, height: float = 120.0) -> BoundingBox:
    return BoundingBox(center_x - width / 2, 0.0, center_x + width / 2, height)


def test_centered_person_has_zero_offset():
    assert normalized_offset(box_at(WIDTH / 2), WIDTH) == pytest.approx(0.0)


def test_offset_is_normalized_to_the_image_edges():
    assert normalized_offset(box_at(0.0), WIDTH) == pytest.approx(-1.0)
    assert normalized_offset(box_at(WIDTH), WIDTH) == pytest.approx(1.0)
    assert normalized_offset(box_at(WIDTH * 0.75), WIDTH) == pytest.approx(0.5)


def test_invalid_image_width_is_rejected():
    with pytest.raises(ValueError):
        normalized_offset(box_at(10.0), 0)


def test_bearing_is_positive_when_person_is_right_of_center():
    assert bearing(box_at(WIDTH * 0.75), WIDTH, HFOV) > 0.0
    assert bearing(box_at(WIDTH * 0.25), WIDTH, HFOV) < 0.0


def test_bearing_at_image_edge_matches_half_the_field_of_view():
    assert bearing(box_at(WIDTH), WIDTH, HFOV) == pytest.approx(HFOV / 2.0)


def test_yaw_error_turns_the_robot_toward_the_person():
    # A person on the right requires a clockwise (negative yaw) rotation under REP-103.
    assert yaw_error(box_at(WIDTH * 0.75), WIDTH, HFOV) < 0.0
    assert yaw_error(box_at(WIDTH * 0.25), WIDTH, HFOV) > 0.0
    assert yaw_error(box_at(WIDTH / 2), WIDTH, HFOV) == pytest.approx(0.0)


def test_largest_prefers_the_biggest_box():
    small = BoundingBox(0.0, 0.0, 10.0, 10.0)
    big = BoundingBox(100.0, 0.0, 200.0, 180.0)
    assert largest([small, big, small]) is big


def test_largest_of_nothing_is_none():
    assert largest([]) is None

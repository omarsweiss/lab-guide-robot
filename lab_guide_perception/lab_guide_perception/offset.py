# Geometry helpers for turning a detected person's bounding box into a steering offset.

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0


def normalized_offset(box: BoundingBox, image_width: int) -> float:
    """Horizontal position of the box center: -1.0 at the left edge, 0.0 centered, +1.0 at the right edge."""
    if image_width <= 0:
        raise ValueError('image_width must be positive')
    half = image_width / 2.0
    return (box.center_x - half) / half


def bearing(box: BoundingBox, image_width: int, horizontal_fov: float) -> float:
    """Angle from the camera's optical axis to the box center, in radians. Positive means the person is to the right."""
    return math.atan(normalized_offset(box, image_width) * math.tan(horizontal_fov / 2.0))


def yaw_error(box: BoundingBox, image_width: int, horizontal_fov: float) -> float:
    """Yaw the robot must rotate to face the person, in radians, following REP-103 (positive is counter-clockwise/left)."""
    return -bearing(box, image_width, horizontal_fov)


def largest(boxes: list[BoundingBox]) -> BoundingBox | None:
    """The most prominent person in frame, used as a stand-in for the nearest one."""
    return max(boxes, key=lambda b: b.area, default=None)

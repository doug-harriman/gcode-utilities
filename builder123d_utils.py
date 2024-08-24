# builder123d_utils.py
#
# Additional utilities for 123D Builder.
#

from typing import List
import numpy as np
from build123d import (
    Wire,
    Face,
)


def wire_is_circle(wire: Wire) -> bool:
    """
    True if the wire is a circle.
    """

    # Determine if the wire is a circle
    # If so, it will have exactly 2 edges and 2 vertices.
    # The edges will have vertices and radii that match.
    # The vertices will be listed in opposite order.
    edges = wire.edges()
    if len(edges) != 2:
        return False

    # Check the radii
    if not np.isclose(edges[0].radius, edges[1].radius):
        return False

    # Check the vertices
    v0 = edges[0].vertices()
    v1 = edges[1].vertices()
    if v0[0] != v1[1]:
        return False

    if v0[1] != v1[0]:
        return False

    return True


# Bind the method to the Wire class
Wire.is_circle = property(lambda self: wire_is_circle(self))


def face_circular_holes(face: Face) -> List[Wire]:
    """
    Return a list of circular holes in the face.
    """
    holes = []
    for wire in face.inner_wires():
        if wire.is_circle:
            holes.append(wire)

    return holes


# Bind the method to the Face class
Face.circular_holes = property(lambda self: face_circular_holes(self))

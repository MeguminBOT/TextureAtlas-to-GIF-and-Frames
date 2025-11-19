"""2D affine transform helpers used by Adobe Spritemap renderer."""

from __future__ import annotations

import numpy as np


class TransformMatrix:
    """2D affine transformation matrix compatible with Adobe Animate exports."""

    def __init__(self, m=None, a=1, b=0, c=0, d=0, e=1, f=0):
        if m is None:
            self.m = np.array([[a, b, c], [d, e, f], [0, 0, 1]], dtype=float)
        else:
            self.m = m

    @classmethod
    def parse(cls, matrix_values):
        """Create a TransformMatrix from an `M3D` list exported by Animate."""
        return cls(a=matrix_values[0], b=matrix_values[4], c=matrix_values[12], d=matrix_values[1], e=matrix_values[5], f=matrix_values[13])

    def data(self):
        """Return Pillow-friendly affine transform tuple."""
        return np.linalg.inv(self.m).reshape(-1)[:6]

    def __matmul__(self, other):
        if not isinstance(other, TransformMatrix):
            raise TypeError(f"expected TransformMatrix, got {type(other)!r}")
        return TransformMatrix(m=self.m @ other.m)

    def __repr__(self):
        a, b, c, d, e, f = self.m.reshape(-1)[:6]
        return f"TransformMatrix(a={a}, b={b}, c={c}, d={d}, e={e}, f={f})"

    def __eq__(self, other):
        return isinstance(other, TransformMatrix) and self.m.tobytes() == other.m.tobytes()

    def __hash__(self):
        return hash(self.m.tobytes())

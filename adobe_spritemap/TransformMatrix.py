""" 
Code taken from PluieElectrique's Texture Atlas Renderer. 
Repository: https://github.com/PluieElectrique/texture-atlas-renderer

Will be edited to fit TextureAtlas to GIF and Frames functionality.
"""

import numpy as np


class TransformMatrix:
    """2D affine transformation matrix."""

    def __init__(self, m=None, a=1, b=0, c=0, d=0, e=1, f=0):
        if m is None:
            self.m = np.array(
                [
                    [a, b, c],
                    [d, e, f],
                    [0, 0, 1],
                ]
            )
        else:
            self.m = m

    @classmethod
    def parse(cls, m):
        """Create a TransformMatrix from an `M3D` list."""
        # The transformation matrix is in column-major order:
        # 0 4  8 12     a b 0 c
        # 1 5  9 13     d e 0 f
        # 2 6 10 14     0 0 1 0
        # 3 7 11 15     0 0 0 1
        return cls(a=m[0], b=m[4], c=m[12], d=m[1], e=m[5], f=m[13])

    def data(self):
        """Return a data tuple for Pillow's affine transformation."""
        # https://pillow.readthedocs.io/en/latest/PIL.html#PIL.ImageTransform.AffineTransform
        #   "For each pixel (x, y) in the output image, the new value is taken
        #   from a position (a x + b y + c, d x + e y + f) in the input image,
        #   rounded to nearest pixel."
        #
        # Our matrix does the opposite (output = self.m @ input), so we invert
        # to get (self.m^-1 @ output = input).
        return np.linalg.inv(self.m).reshape(-1)[:6]

    def __eq__(self, other):
        return type(other) is TransformMatrix and self.m.tobytes() == other.m.tobytes()

    def __hash__(self):
        return hash(self.m.tobytes())

    def __matmul__(self, other):
        if type(other) is not TransformMatrix:
            raise TypeError(
                f"expected type TransformMatrix, but operand has type {type(other)}"
            )
        return TransformMatrix(m=self.m @ other.m)

    def __repr__(self):
        a, b, c, d, e, f = self.m.reshape(-1)[:6]
        return f"TransformMatrix(a={a}, b={b}, c={c}, d={d}, e={e}, f={f})"
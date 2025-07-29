#!/usr/bin/env python3
# -*- coding: utf-8 -*-
class OrderedPacker:
    """
    Ordered packer that preserves frame order but may be less space-efficient.
    Arranges sprites in rows without scrambling their order.
    """

    def __init__(self):
        self.blocks = None
        self.root = None

    def fit(self, blocks):
        self.blocks = blocks
        if not blocks:
            self.root = {"w": 0, "h": 0}
            return

        blocks_per_row = int(self._get_blocks_per_row_estimate())
        blocks_matrix = []

        for i in range(len(self.blocks) // blocks_per_row + 1):
            row = self.blocks[i * blocks_per_row : (i + 1) * blocks_per_row]
            if row:  # Only add non-empty rows
                blocks_matrix.append(row)

        if not blocks_matrix:
            self.root = {"w": 0, "h": 0}
            return

        final_w = self._get_final_width(blocks_matrix)
        final_h = self._get_final_height(blocks_matrix)

        self.root = {"w": final_w, "h": final_h}

        curr_x = 0
        curr_y = 0
        max_heights = [max([b["h"] for b in row]) if row else 0 for row in blocks_matrix]

        for i, row in enumerate(blocks_matrix):
            for bl in row:
                bl["fit"] = {"x": curr_x, "y": curr_y}
                curr_x += bl["w"]
            curr_y += max_heights[i]
            curr_x = 0

    def _get_blocks_per_row_estimate(self):
        if not self.blocks:
            return 1
        tot_area = sum([x["w"] * x["h"] for x in self.blocks])
        estimated_sidelen = tot_area**0.5
        avg_width = self._get_total_width() / len(self.blocks)
        return max(1, int(estimated_sidelen // avg_width))

    def _get_total_width(self):
        return sum([x["w"] for x in self.blocks])

    def _get_final_width(self, rows):
        if not rows:
            return 0
        row_sums = [sum([b["w"] for b in row]) for row in rows if row]
        return max(row_sums) if row_sums else 0

    def _get_final_height(self, rows):
        if not rows:
            return 0
        max_heights = [max([b["h"] for b in row]) if row else 0 for row in rows]
        return sum(max_heights)

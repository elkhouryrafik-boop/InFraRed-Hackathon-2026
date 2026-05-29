#!/usr/bin/env python3
"""Generate a clean, stylized tree billboard sprite -> web/public/tree.png.

Why this exists
---------------
The deck.gl IconLayer needs a single PNG it can billboard + multiply-tint per
tree. We bake a natural-looking tree (rounded green canopy + brown trunk) into a
128x128 transparent PNG, anchored at the BOTTOM-CENTER so the trunk sits on the
ground when IconLayer anchors it there.

The canopy is a soft-shaded green so the tree reads as 3D-ish at a distance. The
sprite is tint-friendly: multiplying by ~white leaves it as a vivid proposed
tree; multiplying by a muted olive mutes it into an "existing" tree, while the
white multiply keeps the trunk brown intact.

Run:  python web/scripts/make_tree_sprite.py
Output is deterministic — committed as web/public/tree.png.
"""

from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter

# ── Canvas ──────────────────────────────────────────────────────────────────
# Supersample 4x then downscale for crisp anti-aliased edges.
SS = 4
W = H = 128
CW, CH = W * SS, H * SS

img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ── Geometry (in supersampled px) ───────────────────────────────────────────
cx = CW // 2

# Trunk: a tapered brown rectangle sitting at the very bottom.
trunk_w = int(CW * 0.085)
trunk_top = int(CH * 0.74)
trunk_bottom = CH - int(CH * 0.015)
trunk_color = (94, 62, 38, 255)          # warm brown
trunk_shadow = (66, 42, 24, 255)         # darker side for a hint of round
draw.rectangle(
    [cx - trunk_w // 2, trunk_top, cx + trunk_w // 2, trunk_bottom],
    fill=trunk_color,
)
# subtle shaded side of trunk
draw.rectangle(
    [cx, trunk_top, cx + trunk_w // 2, trunk_bottom],
    fill=trunk_shadow,
)

# Canopy: three overlapping circles forming a soft rounded crown, plus a base
# blob — gives an organic "tree" silhouette rather than a single ball.
canopy_cx = cx
canopy_cy = int(CH * 0.40)
R = int(CW * 0.30)               # main radius

GREEN_MID = (60, 150, 78)        # base green
GREEN_DARK = (38, 110, 55)       # shadow green
GREEN_LIGHT = (122, 196, 120)    # highlight green


def blob(dx: float, dy: float, r: int, color: tuple[int, int, int, int]) -> None:
    x0, y0 = canopy_cx + dx - r, canopy_cy + dy - r
    x1, y1 = canopy_cx + dx + r, canopy_cy + dy + r
    draw.ellipse([x0, y0, x1, y1], fill=color)


# Build crown from clustered blobs (dark base first, then mid, then highlight).
blob(0, R * 0.55, int(R * 0.95), GREEN_DARK + (255,))
blob(-R * 0.62, R * 0.15, int(R * 0.70), GREEN_DARK + (255,))
blob(R * 0.62, R * 0.15, int(R * 0.70), GREEN_DARK + (255,))

blob(0, 0, R, GREEN_MID + (255,))
blob(-R * 0.55, R * 0.10, int(R * 0.66), GREEN_MID + (255,))
blob(R * 0.55, R * 0.10, int(R * 0.66), GREEN_MID + (255,))
blob(0, -R * 0.45, int(R * 0.72), GREEN_MID + (255,))

# Highlight (sun from upper-left) — a few lighter blobs offset up-left.
blob(-R * 0.30, -R * 0.35, int(R * 0.45), GREEN_LIGHT + (255,))
blob(-R * 0.05, -R * 0.55, int(R * 0.30), GREEN_LIGHT + (255,))
blob(-R * 0.55, -R * 0.05, int(R * 0.26), GREEN_LIGHT + (255,))

# Soft dark rim for definition: draw an outline ring slightly larger, behind.
rim = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
rd = ImageDraw.Draw(rim)
for dx, dy, rr in [
    (0, R * 0.55, R * 0.95),
    (-R * 0.62, R * 0.15, R * 0.70),
    (R * 0.62, R * 0.15, R * 0.70),
    (0, 0, R),
    (0, -R * 0.45, R * 0.72),
]:
    rd.ellipse(
        [
            canopy_cx + dx - rr,
            canopy_cy + dy - rr,
            canopy_cx + dx + rr,
            canopy_cy + dy + rr,
        ],
        fill=(20, 60, 32, 255),
    )
rim = rim.filter(ImageFilter.GaussianBlur(SS * 2))
img = Image.alpha_composite(rim, img)

# Slight overall blur to soften the supersampled blob seams before downscale.
img = img.filter(ImageFilter.GaussianBlur(SS * 0.6))

# ── Downscale to final size (high-quality) ──────────────────────────────────
out = img.resize((W, H), Image.LANCZOS)

dst = os.path.join(os.path.dirname(__file__), "..", "public", "tree.png")
dst = os.path.abspath(dst)
out.save(dst)
print(f"wrote {dst} ({W}x{H})")

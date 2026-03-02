#!/usr/bin/env python3
"""Generate an SVG cut template for Rubik's cube face stickers (3x3 grid).

Each tile gets rounded corners: small radii on the outer perimeter,
large radii on corners facing the center — producing the classic
speed-cube sticker look. The center tile becomes an octagon.

Usage:
    python generate_cuts.py                        # defaults
    python generate_cuts.py --tile 18 --gap 1.5    # 18mm stickers, 1.5mm gap
    python generate_cuts.py --cut-lines            # stroke-only for Cricut
"""

import argparse
import math
from pathlib import Path


def tile_path(x, y, w, h, radii):
    """Return an SVG path `d` string for a rectangle with per-corner radii.

    radii: (top-left, top-right, bottom-right, bottom-left)
    """
    r_tl, r_tr, r_br, r_bl = radii
    return (
        f"M {x + r_tl},{y} "
        f"L {x + w - r_tr},{y} "
        f"A {r_tr},{r_tr} 0 0 1 {x + w},{y + r_tr} "
        f"L {x + w},{y + h - r_br} "
        f"A {r_br},{r_br} 0 0 1 {x + w - r_br},{y + h} "
        f"L {x + r_bl},{y + h} "
        f"A {r_bl},{r_bl} 0 0 1 {x},{y + h - r_bl} "
        f"L {x},{y + r_tl} "
        f"A {r_tl},{r_tl} 0 0 1 {x + r_tl},{y} Z"
    )


def octagon_path(x, y, s, chamfer, corner_r=3):
    """Return an SVG path `d` string for a chamfered-corner octagon with rounded vertices.

    chamfer: the 45° cut distance on each corner (should match r_inner for uniform gaps).
    corner_r: small radius added to each of the 8 vertices.
    """
    c = chamfer
    # Tangent pullback for 135° interior angle
    t = corner_r * math.tan(math.radians(22.5))

    # 8 vertices, clockwise from top-left
    verts = [
        (x + c,     y),
        (x + s - c, y),
        (x + s,     y + c),
        (x + s,     y + s - c),
        (x + s - c, y + s),
        (x + c,     y + s),
        (x,         y + s - c),
        (x,         y + c),
    ]

    parts = []
    n = len(verts)
    for i in range(n):
        prev = verts[(i - 1) % n]
        curr = verts[i]
        nxt = verts[(i + 1) % n]

        # Unit vectors from vertex toward prev and next
        dp = (prev[0] - curr[0], prev[1] - curr[1])
        lp = math.hypot(*dp)
        up = (dp[0] / lp, dp[1] / lp)

        dn = (nxt[0] - curr[0], nxt[1] - curr[1])
        ln = math.hypot(*dn)
        un = (dn[0] / ln, dn[1] / ln)

        # Pull back from vertex along each edge by tangent length
        ax = curr[0] + up[0] * t
        ay = curr[1] + up[1] * t
        bx = curr[0] + un[0] * t
        by = curr[1] + un[1] * t

        if i == 0:
            parts.append(f"M {ax:.4f},{ay:.4f}")
        else:
            parts.append(f"L {ax:.4f},{ay:.4f}")

        parts.append(f"A {corner_r},{corner_r} 0 0 1 {bx:.4f},{by:.4f}")

    parts.append("Z")
    return " ".join(parts)


# For each (row, col), which corners face the center (1,1)?
# Order: top-left, top-right, bottom-right, bottom-left
INNER_CORNERS = {
    (0, 0): (False, False, True,  False),
    (0, 1): (False, False, True,  True),
    (0, 2): (False, False, False, True),
    (1, 0): (False, True,  True,  False),
    (1, 2): (True,  False, False, True),
    (2, 0): (False, True,  False, False),
    (2, 1): (True,  True,  False, False),
    (2, 2): (True,  False, False, False),
}


def generate_face_svg(tile=100, gap=10, padding=10, r_outer=12, r_inner=22,
                      oct_straight=0.55, r_oct_corner=3, color="#33A64B",
                      cut_lines=False, inset=5):
    """Generate SVG content for one Rubik's cube face."""
    total = tile * 3 + gap * 2 + padding * 2
    paths = []

    # Which edges of each outer tile face the center: (top, right, bottom, left)
    INNER_EDGES = {
        (0, 0): (False, True,  True,  False),
        (0, 1): (False, False, True,  False),
        (0, 2): (False, False, True,  True),
        (1, 0): (False, True,  False, False),
        (1, 2): (False, False, False, True),
        (2, 0): (True,  True,  False, False),
        (2, 1): (True,  False, False, False),
        (2, 2): (True,  False, False, True),
    }

    for row in range(3):
        for col in range(3):
            x = padding + col * (tile + gap)
            y = padding + row * (tile + gap)

            if row == 1 and col == 1:
                oct_chamfer = tile * (1 - oct_straight) / 2
                d = octagon_path(x, y, tile, chamfer=oct_chamfer, corner_r=r_oct_corner)
            else:
                # Inset inner-facing edges away from center
                edges = INNER_EDGES[(row, col)]
                tx, ty, tw, th = x, y, tile, tile
                if edges[0]:  # top faces center → move top down
                    ty += inset
                    th -= inset
                if edges[2]:  # bottom faces center → shrink height
                    th -= inset
                if edges[3]:  # left faces center → move left edge right
                    tx += inset
                    tw -= inset
                if edges[1]:  # right faces center → shrink width
                    tw -= inset

                mask = INNER_CORNERS[(row, col)]
                radii = tuple(r_inner if facing else r_outer for facing in mask)
                d = tile_path(tx, ty, tw, th, radii)

            paths.append(f'    <path d="{d}"/>')

    paths_str = "\n".join(paths)

    if cut_lines:
        style = f'fill="none" stroke="{color}" stroke-width="0.5"'
    else:
        style = f'fill="{color}"'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="0 0 {total} {total}" width="{total}" height="{total}">\n'
        f'  <g {style}>\n'
        f'{paths_str}\n'
        f'  </g>\n'
        f'</svg>\n'
    )


def main():
    p = argparse.ArgumentParser(description="Rubik's cube sticker cut SVG")
    p.add_argument("--tile", type=float, default=100, help="tile size (default 100)")
    p.add_argument("--gap", type=float, default=10, help="gap between tiles (default 10)")
    p.add_argument("--padding", type=float, default=10, help="outer padding (default 10)")
    p.add_argument("--r-outer", type=float, default=12, help="outer corner radius (default 12)")
    p.add_argument("--r-inner", type=float, default=22, help="inner corner radius (default 22)")
    p.add_argument("--inset", type=float, default=5,
                    help="how far to pull inner edges away from center (default 5)")
    p.add_argument("--oct-straight", type=float, default=0.55,
                    help="octagon straight-side length as fraction of tile (default 0.55)")
    p.add_argument("--r-oct", type=float, default=3, help="octagon corner radius (default 3)")
    p.add_argument("--color", default="#33A64B", help="fill/stroke color (default #33A64B)")
    p.add_argument("--cut-lines", action="store_true",
                    help="stroke-only output for cutting machines")
    p.add_argument("-o", "--output", default="rubiks_face.svg", help="output filename")
    args = p.parse_args()

    svg = generate_face_svg(
        tile=args.tile, gap=args.gap, padding=args.padding,
        r_outer=args.r_outer, r_inner=args.r_inner,
        oct_straight=args.oct_straight, r_oct_corner=args.r_oct,
        color=args.color, cut_lines=args.cut_lines, inset=args.inset,
    )

    Path(args.output).write_text(svg)
    print(f"Written: {args.output}")


if __name__ == "__main__":
    main()

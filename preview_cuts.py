#!/usr/bin/env python3
"""Extract 9 cells from each Gemini 3x3 grid image and recompose them
onto a new canvas aligned with the SVG cut template.

For each cell, we auto-detect the colored content bounds (skipping any
dark outlines or white padding), then center and scale it to fill the
cut shape area with minimal cropping.
"""

import glob
from io import BytesIO
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image

from generate_cuts import generate_face_svg

INPUT_DIR = Path("/home/maustin/rubiksmaria")
OUTPUT_DIR = INPUT_DIR / "previews"
OUTPUT_DIR.mkdir(exist_ok=True)

# --- Cut template parameters ---
TILE = 100
GAP = 10
PADDING = 10
R_OUTER = 12
R_INNER = 35
OCT_STRAIGHT = 0.55
R_OCT = 3
TOTAL = TILE * 3 + GAP * 2 + PADDING * 2  # 340

OUT_PX = 2048
SCALE = OUT_PX / TOTAL

# Bleed beyond tile edge in SVG units
BLEED = 2


def auto_trim_cell(cell_img):
    """Trim dark outlines and white borders from a cell image.

    Scans inward from each edge to find where the main colored content
    starts (not black outline, not white background).
    """
    arr = np.array(cell_img.convert("RGB")).astype(float)
    h, w, _ = arr.shape

    # A pixel is "border" if it's very dark (outline) or very bright (white gap)
    brightness = arr.mean(axis=2)
    is_dark = brightness < 50
    is_white = brightness > 240

    # For each edge, find how far in the border extends
    # by checking when majority of pixels in a row/col are content
    is_border = is_dark | is_white

    max_trim = min(h, w) // 6

    def scan_rows_from_top(arr2d, max_scan):
        for i in range(max_scan):
            if arr2d[i, :].mean() < 0.4:
                return i
        return max_scan

    top = scan_rows_from_top(is_border, max_trim)
    bottom = scan_rows_from_top(is_border[::-1, :], max_trim)
    left = scan_rows_from_top(is_border.T, max_trim)
    right = scan_rows_from_top(is_border.T[::-1, :], max_trim)

    # Ensure we trim at least a few pixels and don't over-trim
    top = max(top, 2)
    bottom = max(bottom, 2)
    left = max(left, 2)
    right = max(right, 2)

    return cell_img.crop((left, top, w - right, h - bottom))


def extract_cells(img):
    """Split image into 3x3 grid using even thirds, then auto-trim each cell."""
    w, h = img.size
    cw = w / 3
    ch = h / 3

    cells = []
    for row in range(3):
        row_cells = []
        for col in range(3):
            x1 = round(col * cw)
            y1 = round(row * ch)
            x2 = round((col + 1) * cw)
            y2 = round((row + 1) * ch)
            raw_cell = img.crop((x1, y1, x2, y2))
            trimmed = auto_trim_cell(raw_cell)
            row_cells.append(trimmed)
        cells.append(row_cells)
    return cells


def main():
    # Generate red cut-line overlay SVG
    overlay_svg = generate_face_svg(
        tile=TILE, gap=GAP, padding=PADDING,
        r_outer=R_OUTER, r_inner=R_INNER,
        oct_straight=OCT_STRAIGHT, r_oct_corner=R_OCT,
        color="#FF0000", cut_lines=True,
    )
    overlay_svg = overlay_svg.replace('stroke-width="0.5"', 'stroke-width="2"')
    overlay_png = cairosvg.svg2png(
        bytestring=overlay_svg.encode(),
        output_width=OUT_PX, output_height=OUT_PX,
    )
    overlay_img = Image.open(BytesIO(overlay_png)).convert("RGBA")

    for img_path in sorted(glob.glob(str(INPUT_DIR / "Gemini_*.png"))):
        img = Image.open(img_path).convert("RGBA")
        cells = extract_cells(img)

        canvas = Image.new("RGBA", (OUT_PX, OUT_PX), (255, 255, 255, 255))

        for row in range(3):
            for col in range(3):
                cell_img = cells[row][col]

                # Tile center in SVG coords
                tile_cx = PADDING + col * (TILE + GAP) + TILE / 2
                tile_cy = PADDING + row * (TILE + GAP) + TILE / 2

                # Target size with bleed
                target_w = round((TILE + 2 * BLEED) * SCALE)
                target_h = round((TILE + 2 * BLEED) * SCALE)

                # Center in pixels
                px_cx = tile_cx * SCALE
                px_cy = tile_cy * SCALE

                cell_resized = cell_img.resize((target_w, target_h), Image.LANCZOS)

                paste_x = round(px_cx - target_w / 2)
                paste_y = round(px_cy - target_h / 2)

                canvas.paste(cell_resized, (paste_x, paste_y))

        composite = Image.alpha_composite(canvas, overlay_img)
        out_name = f"preview_{Path(img_path).stem}.png"
        out_path = OUTPUT_DIR / out_name
        composite.save(out_path)
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--bleed", type=float, default=BLEED,
                   help="SVG units of bleed beyond tile edge (default 2). "
                        "Lower = less image loss, higher = more coverage safety.")
    args = p.parse_args()
    BLEED = args.bleed
    print(f"Using bleed={BLEED}")
    main()

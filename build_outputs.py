#!/usr/bin/env python3
"""Generate production outputs for Cricut from 3x3 grid images.

Outputs per image:
  1. composites/<name>.png  — recomposed image (no cut overlay), white background
  2. masked/<name>.png      — cut shapes applied as mask, transparent background
  3. pdf/<name>.pdf         — print-and-cut: masked image with cut lines, transparent bg

Also generates:
  cuts/rubiks_face.svg      — standalone cut SVG for Cricut

Usage:
    python build_outputs.py                # bleed=1 (default)
    python build_outputs.py --bleed 0.5    # tighter
"""

import argparse
import glob
from io import BytesIO
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image

from generate_cuts import generate_face_svg

INPUT_DIR = Path("/home/maustin/rubiksmaria")

# --- Cut template parameters ---
TILE = 100
GAP = 10
PADDING = 10
R_OUTER = 12
R_INNER = 22
INSET = 5
OCT_STRAIGHT = 0.55
R_OCT = 3
TOTAL = TILE * 3 + GAP * 2 + PADDING * 2  # 340

OUT_PX = 2048
SCALE = OUT_PX / TOTAL


def auto_trim_cell(cell_img):
    """Trim dark outlines and white borders from a cell image."""
    arr = np.array(cell_img.convert("RGB")).astype(float)
    h, w, _ = arr.shape

    brightness = arr.mean(axis=2)
    is_border = (brightness < 50) | (brightness > 240)

    max_trim = min(h, w) // 6

    def scan_rows_from_top(arr2d, max_scan):
        for i in range(max_scan):
            if arr2d[i, :].mean() < 0.4:
                return i
        return max_scan

    top = max(scan_rows_from_top(is_border, max_trim), 2)
    bottom = max(scan_rows_from_top(is_border[::-1, :], max_trim), 2)
    left = max(scan_rows_from_top(is_border.T, max_trim), 2)
    right = max(scan_rows_from_top(is_border.T[::-1, :], max_trim), 2)

    return cell_img.crop((left, top, w - right, h - bottom))


def extract_cells(img):
    """Split image into 3x3 grid using even thirds, auto-trim each cell."""
    w, h = img.size
    cw, ch = w / 3, h / 3

    cells = []
    for row in range(3):
        row_cells = []
        for col in range(3):
            x1 = round(col * cw)
            y1 = round(row * ch)
            x2 = round((col + 1) * cw)
            y2 = round((row + 1) * ch)
            row_cells.append(auto_trim_cell(img.crop((x1, y1, x2, y2))))
        cells.append(row_cells)
    return cells


def recompose(cells, bleed):
    """Place cells onto a transparent canvas aligned with the cut template."""
    canvas = Image.new("RGBA", (OUT_PX, OUT_PX), (0, 0, 0, 0))

    # Which edges face the center: (top, right, bottom, left)
    INNER_EDGES = {
        (0, 0): (False, True,  True,  False),
        (0, 1): (False, False, True,  False),
        (0, 2): (False, False, True,  True),
        (1, 0): (False, True,  False, False),
        (1, 1): (False, False, False, False),
        (1, 2): (False, False, False, True),
        (2, 0): (True,  True,  False, False),
        (2, 1): (True,  False, False, False),
        (2, 2): (True,  False, False, True),
    }

    for row in range(3):
        for col in range(3):
            cell_img = cells[row][col]

            # Start with the original tile rectangle
            tx = PADDING + col * (TILE + GAP)
            ty = PADDING + row * (TILE + GAP)
            tw, th = TILE, TILE

            # Apply inset on inner-facing edges
            edges = INNER_EDGES[(row, col)]
            if edges[0]:  # top
                ty += INSET
                th -= INSET
            if edges[2]:  # bottom
                th -= INSET
            if edges[3]:  # left
                tx += INSET
                tw -= INSET
            if edges[1]:  # right
                tw -= INSET

            tile_cx = tx + tw / 2
            tile_cy = ty + th / 2

            target_w = round((tw + 2 * bleed) * SCALE)
            target_h = round((th + 2 * bleed) * SCALE)

            px_cx = tile_cx * SCALE
            px_cy = tile_cy * SCALE

            cell_resized = cell_img.resize((target_w, target_h), Image.LANCZOS)

            paste_x = round(px_cx - target_w / 2)
            paste_y = round(px_cy - target_h / 2)

            canvas.paste(cell_resized, (paste_x, paste_y))

    return canvas


def render_cut_mask():
    """Render the cut shapes as a white-on-transparent mask."""
    mask_svg = generate_face_svg(
        tile=TILE, gap=GAP, padding=PADDING,
        r_outer=R_OUTER, r_inner=R_INNER,
        oct_straight=OCT_STRAIGHT, r_oct_corner=R_OCT,
        color="#FFFFFF", cut_lines=False, inset=INSET,
    )
    png_data = cairosvg.svg2png(
        bytestring=mask_svg.encode(),
        output_width=OUT_PX, output_height=OUT_PX,
    )
    mask_img = Image.open(BytesIO(png_data)).convert("L")
    return mask_img


def main():
    p = argparse.ArgumentParser(description="Build Cricut production outputs")
    p.add_argument("--bleed", type=float, default=1,
                   help="SVG units of bleed beyond tile edge (default 1)")
    args = p.parse_args()
    bleed = args.bleed
    print(f"Using bleed={bleed}")

    # Create output directories
    composites_dir = INPUT_DIR / "composites"
    masked_dir = INPUT_DIR / "masked"
    pdf_dir = INPUT_DIR / "pdf"
    cuts_dir = INPUT_DIR / "cuts"
    for d in [composites_dir, masked_dir, pdf_dir, cuts_dir]:
        d.mkdir(exist_ok=True)

    # 1. Generate standalone cut SVG
    cut_svg = generate_face_svg(
        tile=TILE, gap=GAP, padding=PADDING,
        r_outer=R_OUTER, r_inner=R_INNER,
        oct_straight=OCT_STRAIGHT, r_oct_corner=R_OCT,
        color="#000000", cut_lines=True, inset=INSET,
    )
    cut_svg_path = cuts_dir / "rubiks_face.svg"
    cut_svg_path.write_text(cut_svg)
    print(f"Saved: {cut_svg_path}")

    # Render cut mask (filled shapes)
    mask = render_cut_mask()

    # Render thin cut lines for PDF overlay
    overlay_svg = generate_face_svg(
        tile=TILE, gap=GAP, padding=PADDING,
        r_outer=R_OUTER, r_inner=R_INNER,
        oct_straight=OCT_STRAIGHT, r_oct_corner=R_OCT,
        color="#888888", cut_lines=True, inset=INSET,
    )
    overlay_svg = overlay_svg.replace('stroke-width="0.5"', 'stroke-width="1"')
    overlay_png = cairosvg.svg2png(
        bytestring=overlay_svg.encode(),
        output_width=OUT_PX, output_height=OUT_PX,
    )
    overlay_img = Image.open(BytesIO(overlay_png)).convert("RGBA")

    for img_path in sorted(glob.glob(str(INPUT_DIR / "inputs" / "*.png"))):
        img = Image.open(img_path).convert("RGBA")
        name = Path(img_path).stem
        cells = extract_cells(img)

        # Recompose on transparent canvas
        recomposed = recompose(cells, bleed)

        # --- Option 1: Composite (white background, no cut lines) ---
        white_bg = Image.new("RGBA", (OUT_PX, OUT_PX), (255, 255, 255, 255))
        composite = Image.alpha_composite(white_bg, recomposed)
        comp_path = composites_dir / f"{name}.png"
        composite.convert("RGB").save(comp_path)
        print(f"Saved: {comp_path}")

        # --- Option 2: Masked PNG (cut shapes as transparency mask) ---
        masked = recomposed.copy()
        # Apply the cut-shape mask to the alpha channel
        r, g, b, a = masked.split()
        # Combine existing alpha with the cut mask
        combined_alpha = Image.fromarray(
            np.minimum(np.array(a), np.array(mask))
        )
        masked.putalpha(combined_alpha)
        masked_path = masked_dir / f"{name}.png"
        masked.save(masked_path)
        print(f"Saved: {masked_path}")

        # --- Option 3: PDF with masked image + cut lines ---
        pdf_composite = Image.alpha_composite(masked, overlay_img)
        pdf_path = pdf_dir / f"{name}.pdf"
        pdf_composite.save(pdf_path, "PDF", resolution=300)
        print(f"Saved: {pdf_path}")

    print("\nDone! Output directories:")
    print(f"  composites/  — recomposed PNGs (white bg, no cut lines)")
    print(f"  masked/      — cut-masked PNGs (transparent bg)")
    print(f"  cuts/        — standalone cut SVG")
    print(f"  pdf/         — print-and-cut PDFs (masked + cut lines)")


if __name__ == "__main__":
    main()

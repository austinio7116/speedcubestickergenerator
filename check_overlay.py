#!/usr/bin/env python3
"""Overlay the existing cut-line SVG onto photo.png for visual alignment checking.

Usage:
    python check_overlay.py
    python check_overlay.py --opacity 0.6
    python check_overlay.py --line-width 2.0
"""

import argparse
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description="Overlay cut lines on photo for checking")
    p.add_argument("--photo", default="photo.png", help="reference photo (default photo.png)")
    p.add_argument("--svg", default="rubiks_face_cutlines.svg", help="cut-lines SVG")
    p.add_argument("--output", default="check_overlay.png", help="output filename")
    p.add_argument("--opacity", type=float, default=0.7, help="photo opacity (0-1, default 0.7)")
    p.add_argument("--line-width", type=float, default=3.0,
                    help="SVG stroke-width override (default 3.0)")
    args = p.parse_args()

    photo = Image.open(args.photo).convert("RGBA")
    w, h = photo.size

    # Read the SVG and thicken the stroke for visibility at photo resolution
    svg_text = Path(args.svg).read_text()
    svg_text = svg_text.replace('stroke-width="0.5"', f'stroke-width="{args.line_width}"')

    # Render SVG at photo resolution
    png_bytes = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=w, output_height=h)
    cuts = Image.open(__import__("io").BytesIO(png_bytes)).convert("RGBA")

    # Dim the photo slightly so cut lines stand out
    dimmed = Image.blend(Image.new("RGBA", photo.size, (0, 0, 0, 255)), photo, args.opacity)

    # Composite cut lines on top
    result = Image.alpha_composite(dimmed, cuts)
    result.save(args.output)
    print(f"Written: {args.output}  ({w}x{h})")


if __name__ == "__main__":
    main()

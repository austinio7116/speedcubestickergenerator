# Speed Cube Sticker Generator

Generate custom sticker sets for a 3x3 Rubik's cube. Designed for use with a Cricut cutting machine and the [ROXENDA Speed Cube 3x3x3](https://www.amazon.co.uk/dp/B089VWZK9B).

## How it works

1. Prepare your input images (see requirements below)
2. Place them in the project root as `*.png` files
3. Run the build pipeline to produce print-and-cut outputs

The cut template accounts for the cube's sticker geometry — rounded corners, gaps between tiles, and the octagonal center sticker.

## Input image requirements

Each input image should be a **square PNG** containing a **3x3 grid** of artwork — one cell per sticker face. The image is split into equal thirds in each direction, so:

- The grid should be evenly divided into 9 cells (3 rows x 3 columns)
- Each cell contains the artwork for one sticker
- Dark outlines or borders between cells are automatically trimmed
- Higher resolution images produce better results (2048x2048 or above recommended)
- Images must be named with a `Gemini_Generated_Image_` prefix (e.g. `Gemini_Generated_Image_myface.png`) or edit the glob pattern in `build_outputs.py` to match your filenames

## Setup

```bash
pip install pillow cairosvg numpy
```

## Usage

### Generate cut templates

```bash
python generate_cuts.py                        # filled SVG (default params)
python generate_cuts.py --cut-lines            # stroke-only SVG for Cricut
python generate_cuts.py --r-inner 22 --inset 5 # customise corner radii and edge inset
```

### Build all outputs

```bash
python build_outputs.py                # default bleed=1
python build_outputs.py --bleed 0.5    # tighter bleed
```

This produces:

| Directory      | Contents                                              |
|----------------|-------------------------------------------------------|
| `composites/`  | Recomposed PNGs with white background, no cut lines   |
| `masked/`      | Cut-shaped PNGs with transparent background           |
| `pdf/`         | Print-and-cut PDFs (masked image + cut line overlay)  |
| `cuts/`        | Standalone cut SVG for Cricut                         |

### Check alignment against the real cube

```bash
python check_overlay.py
```

Overlays the cut lines onto `photo.png` (a reference photo of the actual cube) so you can visually verify the shapes match the real stickers.

### Preview cut lines on artwork

```bash
python preview_cuts.py
```

Generates preview images in `previews/` showing the artwork with red cut line overlays.

## Key parameters

| Parameter       | Default | Description                                        |
|-----------------|---------|----------------------------------------------------|
| `--tile`        | 100     | Sticker tile size in SVG units                     |
| `--gap`         | 10      | Gap between tiles                                  |
| `--padding`     | 10      | Outer border padding                               |
| `--r-outer`     | 12      | Corner radius on outer edges                       |
| `--r-inner`     | 22      | Corner radius on inner edges (facing center)       |
| `--inset`       | 5       | How far to pull inner edges away from center       |
| `--oct-straight`| 0.55    | Center octagon straight-side ratio                 |
| `--bleed`       | 1       | Bleed beyond tile edge (build_outputs only)        |

## Reference files

- `photo.png` — photo of the actual ROXENDA cube used to verify cut line alignment

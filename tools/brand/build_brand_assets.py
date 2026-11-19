"""Build production logo files from the approved raster concept.

The concept is flat two-color artwork (forest green + harvest gold) on a solid cream
background. Each pixel is un-mixed against the background to recover clean coverage
(alpha) per ink, re-colored with the exact brand palette, and traced to vector paths
with potrace. Outputs go to fallah-brand-assets/production/.

Usage (from repo root):
    python -m venv /tmp/brandvenv && /tmp/brandvenv/bin/pip install pillow numpy scipy potracer cairosvg
    /tmp/brandvenv/bin/python tools/brand/build_brand_assets.py
"""

from pathlib import Path

import numpy as np
import potrace
from PIL import Image, ImageFilter
from scipy import ndimage
import cairosvg
import io

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "fallah-brand-assets" / "fallah-and-sons-logo-concept.png"
OUT = ROOT / "fallah-brand-assets" / "production"

GREEN = np.array([0x17, 0x3F, 0x35], dtype=float)
GOLD = np.array([0xB5, 0x8A, 0x45], dtype=float)
CREAM = (0xF6, 0xF1, 0xE7)
RICE_WHITE = (0xFF, 0xFE, 0xFA)
GREEN_HEX, GOLD_HEX, CREAM_HEX = "#173F35", "#B58A45", "#F6F1E7"


def unmix(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (green_alpha, gold_alpha) in 0..1 by projecting each pixel from bg toward each ink."""
    border = np.concatenate([rgb[:8].reshape(-1, 3), rgb[-8:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    diff = rgb - bg
    alphas, residuals = [], []
    for ink in (GREEN, GOLD):
        direction = ink - bg
        t = (diff @ direction) / (direction @ direction)
        t = np.clip(t, 0, 1)
        residual = np.linalg.norm(diff - t[..., None] * direction, axis=-1)
        alphas.append(t)
        residuals.append(residual)
    green_wins = residuals[0] <= residuals[1]
    green_a = np.where(green_wins, alphas[0], 0.0)
    gold_a = np.where(~green_wins, alphas[1], 0.0)
    # Remove faint noise (paper texture/jpeg artefacts) and harden near-solid coverage.
    for a in (green_a, gold_a):
        a[a < 0.08] = 0
        a[a > 0.92] = 1
    return green_a, gold_a


def rgba_from(alpha_layers: list[tuple[np.ndarray, tuple[int, int, int]]]) -> Image.Image:
    h, w = alpha_layers[0][0].shape
    out = np.zeros((h, w, 4), dtype=float)
    total = np.zeros((h, w))
    for alpha, color in alpha_layers:
        out[..., :3] += alpha[..., None] * np.array(color, dtype=float)
        total += alpha
    total = np.clip(total, 0, 1)
    nonzero = total > 0
    out[nonzero, :3] /= np.maximum(total[nonzero, None], 1e-6)
    out[..., 3] = total * 255
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def split_emblem_and_wordmark(coverage: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Boolean masks for the emblem and the wordmark.

    The emblem tip and the tallest letters overlap vertically, so shapes are assigned by
    connected component: anything centred above the narrowest row between them is emblem.
    """
    solid = coverage > 0.05
    rows = solid.sum(axis=1)
    filled = np.where(rows > 0)[0]
    top, bottom = filled[0], filled[-1]
    lower = top + int((bottom - top) * 0.55)
    upper = top + int((bottom - top) * 0.80)
    split = lower + int(np.argmin(rows[lower:upper]))
    labels, count = ndimage.label(solid, structure=np.ones((3, 3)))
    centers = ndimage.center_of_mass(solid, labels, range(1, count + 1))
    emblem_ids = [i + 1 for i, (cy, _) in enumerate(centers) if cy < split]
    emblem = np.isin(labels, emblem_ids)
    wordmark = solid & ~emblem
    return emblem, wordmark


def bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def crop(img: Image.Image, box, pad: int) -> Image.Image:
    x0, y0, x1, y1 = box
    piece = img.crop((x0, y0, x1, y1))
    canvas = Image.new("RGBA", (piece.width + 2 * pad, piece.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(piece, (pad, pad))
    return canvas


def recolor(img: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    alpha = img.getchannel("A")
    solid = Image.new("RGBA", img.size, color + (255,))
    solid.putalpha(alpha)
    return solid


def on_background(img: Image.Image, color, pad: int = 0) -> Image.Image:
    canvas = Image.new("RGB", (img.width + 2 * pad, img.height + 2 * pad), color)
    canvas.paste(img, (pad, pad), img)
    return canvas


def trace_paths(alpha: np.ndarray, offset=(0, 0)) -> str:
    """Trace a coverage mask (≥50%) into an SVG path 'd' attribute using potrace."""
    bitmap = potrace.Bitmap(alpha < 0.5)  # potracer: False pixels are ink
    plist = bitmap.trace(turdsize=6, alphamax=1.0, opticurve=True, opttolerance=0.2)
    ox, oy = offset
    parts = []
    for curve in plist:
        sx, sy = curve.start_point.x, curve.start_point.y
        parts.append(f"M{sx - ox:.1f},{sy - oy:.1f}")
        for segment in curve.segments:
            ex, ey = segment.end_point.x, segment.end_point.y
            if segment.is_corner:
                cx, cy = segment.c.x, segment.c.y
                parts.append(f"L{cx - ox:.1f},{cy - oy:.1f}L{ex - ox:.1f},{ey - oy:.1f}")
            else:
                ax, ay, bx, by = segment.c1.x, segment.c1.y, segment.c2.x, segment.c2.y
                parts.append(f"C{ax - ox:.1f},{ay - oy:.1f} {bx - ox:.1f},{by - oy:.1f} {ex - ox:.1f},{ey - oy:.1f}")
        parts.append("Z")
    return "".join(parts)


def svg_document(width: int, height: int, layers: list[tuple[str, str]], title: str) -> str:
    paths = "\n".join(f'  <path fill="{color}" fill-rule="evenodd" d="{d}"/>' for d, color in layers if d)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{title}">\n  <title>{title}</title>\n{paths}\n</svg>\n'
    )


def favicon_master(size: int = 1024) -> Image.Image:
    """Raster icon rendered from the hand-drawn favicon SVG."""
    png = cairosvg.svg2png(bytestring=FAVICON_SVG.encode("utf-8"), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


FAVICON_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="فلاح و پسران">
  <title>فلاح و پسران</title>
  <rect width="64" height="64" rx="14" fill="{GREEN_HEX}"/>
  <path fill="{CREAM_HEX}" d="M32 55C28.6 46.4 20.6 41.6 8.5 30.5C10.2 43.6 18.6 51.6 32 55Z"/>
  <path fill="{CREAM_HEX}" d="M32 55C35.4 46.4 43.4 41.6 55.5 30.5C53.8 43.6 45.4 51.6 32 55Z"/>
  <ellipse cx="32" cy="27" rx="6.6" ry="16.5" fill="{GOLD_HEX}"/>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(Image.open(SOURCE).convert("RGB")).astype(float)
    green_a, gold_a = unmix(rgb)
    coverage = np.maximum(green_a, gold_a)
    full = rgba_from([(green_a, tuple(GREEN.astype(int))), (gold_a, tuple(GOLD.astype(int)))])

    emblem_mask, word_mask = split_emblem_and_wordmark(coverage)
    emblem_box = bbox(emblem_mask)
    word_box = bbox(word_mask)
    lock_box = bbox(emblem_mask | word_mask)

    def only(mask):
        image = full.copy()
        alpha = np.asarray(image.getchannel("A")).copy()
        alpha[~mask] = 0
        image.putalpha(Image.fromarray(alpha))
        return image

    pad = 24
    emblem = crop(only(emblem_mask), emblem_box, pad)
    wordmark = crop(only(word_mask), word_box, pad)
    stacked = crop(full, lock_box, pad)

    # Horizontal (RTL reading order: emblem on the right, wordmark to its left).
    target_h = emblem.height
    word_scaled = wordmark.resize((int(wordmark.width * target_h * 0.55 / wordmark.height), int(target_h * 0.55)),
                                  Image.LANCZOS)
    gap = 36
    horizontal = Image.new("RGBA", (word_scaled.width + gap + emblem.width, target_h), (0, 0, 0, 0))
    horizontal.paste(word_scaled, (0, (target_h - word_scaled.height) // 2), word_scaled)
    horizontal.paste(emblem, (word_scaled.width + gap, 0), emblem)

    files = {
        "fallah-lockup-stacked.png": stacked,
        "fallah-lockup-horizontal.png": horizontal,
        "fallah-emblem.png": emblem,
        "fallah-wordmark.png": wordmark,
        "fallah-lockup-stacked-mono-green.png": recolor(stacked, tuple(GREEN.astype(int))),
        "fallah-lockup-stacked-mono-cream.png": recolor(stacked, CREAM),
        "fallah-emblem-mono-green.png": recolor(emblem, tuple(GREEN.astype(int))),
        "fallah-emblem-mono-cream.png": recolor(emblem, CREAM),
        "fallah-lockup-horizontal-mono-cream.png": recolor(horizontal, CREAM),
    }
    for name, image in files.items():
        image.save(OUT / name, optimize=True)

    # Previews on intended backgrounds (for the usage guide).
    on_background(stacked, CREAM, 40).save(OUT / "preview-stacked-on-cream.png")
    on_background(recolor(stacked, CREAM), tuple(GREEN.astype(int)), 40).save(OUT / "preview-stacked-on-green.png")

    # Vector versions traced from the clean coverage masks.
    def traced(box, mask, name, title):
        x0, y0, x1, y1 = box
        g = np.where(mask, green_a, 0)[y0:y1, x0:x1]
        o = np.where(mask, gold_a, 0)[y0:y1, x0:x1]
        g_pad = np.pad(g, pad)
        o_pad = np.pad(o, pad)
        width, height = g_pad.shape[1], g_pad.shape[0]
        layers = [(trace_paths(g_pad), GREEN_HEX), (trace_paths(o_pad), GOLD_HEX)]
        (OUT / name).write_text(svg_document(width, height, layers, title), encoding="utf-8")
        mono = [(trace_paths(np.maximum(g_pad, o_pad)), "currentColor")]
        (OUT / name.replace(".svg", "-mono.svg")).write_text(svg_document(width, height, mono, title), "utf-8")

    traced(emblem_box, emblem_mask, "fallah-emblem.svg", "نشان فلاح و پسران")
    traced(lock_box, emblem_mask | word_mask, "fallah-lockup-stacked.svg", "فلاح و پسران")

    # App icons and favicons from the simplified mark.
    (OUT / "favicon.svg").write_text(FAVICON_SVG, encoding="utf-8")
    master = favicon_master(1024)
    master.save(OUT / "icon-1024.png")
    for size in (512, 192, 180, 32, 16):
        name = "apple-touch-icon.png" if size == 180 else f"icon-{size}.png"
        master.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
    # Maskable icon: full-bleed background with the mark inside the 80% safe zone.
    maskable = Image.new("RGBA", (512, 512), GREEN_HEX)  # full-bleed for maskable safe zone
    inner = favicon_master(410)
    maskable.paste(inner, (51, 51), inner)
    maskable.save(OUT / "icon-maskable-512.png", optimize=True)
    master.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    # Open Graph card.
    og = Image.new("RGB", (1200, 630), CREAM)
    lock = stacked.copy()
    lock.thumbnail((520, 520), Image.LANCZOS)
    og.paste(lock, ((1200 - lock.width) // 2, (630 - lock.height) // 2), lock)
    og.filter(ImageFilter.SMOOTH)
    og.save(OUT / "og-image.png", optimize=True)
    print("built", len(list(OUT.iterdir())), "files in", OUT)


if __name__ == "__main__":
    main()

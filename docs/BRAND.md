# Brand usage — فلاح و پسران

The identity comes from the owner-supplied concept
`fallah-brand-assets/fallah-and-sons-logo-concept.png`: two rice panicles around one grain, with
the Persian name below. `tools/brand/build_brand_assets.py` separates the two inks from the cream
background, snaps them to the exact palette, and traces vector paths. Every variant below derives
from that one artwork; nothing was redrawn by hand.

No trademark or similarity search has been done (see [DECISIONS.md](DECISIONS.md)).

## Files (`fallah-brand-assets/production/`)

| File | Use |
|---|---|
| `fallah-lockup-stacked.svg` / `.png` | Primary logo: emblem above name. Transparent. |
| `fallah-lockup-horizontal.png` | Header and narrow bars: emblem beside name. |
| `fallah-emblem.svg` / `.png` | Emblem only: avatars, stamps, favicon source, small spaces. |
| `fallah-wordmark.png` | Name only, where the emblem already appears nearby. |
| `*-mono.svg` | One-colour vector (`currentColor`), for engraving, stamps, single-colour print. |
| `*-mono-green.png` | One colour on light backgrounds. |
| `*-mono-cream.png` | One colour on brand green or dark photos. |
| `favicon.svg`, `favicon.ico`, `icon-16/32/192/512/1024.png`, `icon-maskable-512.png`, `apple-touch-icon.png` | Browser and app icons (emblem on cream tile; maskable has safe padding). |
| `og-image.png` | 1200×630 social preview. |
| `preview-stacked-on-cream.png`, `preview-stacked-on-green.png` | Reference renders only. |

## Colours

| Token | Hex | Use |
|---|---|---|
| Forest green | `#173F35` | Primary ink, header/footer, primary buttons |
| Rice white | `#FFFEFA` | Page background |
| Warm cream | `#F6F1E7` | Sections, tiles, icon background |
| Harvest gold | `#B58A45` | Emblem grains, accents, focus ring. Not for small text (contrast) |
| Ink | `#202B26` | Body text |

Two-colour logo: green + gold on rice white or cream. On green or photos use the cream monochrome.
Never place the two-colour logo on gold or busy imagery.

## Clear space and minimum size

- **Clear space:** keep at least the height of the central rice grain (about one quarter of the
  emblem height) empty on every side. Nothing (text, edges, other logos) enters this area.
- **Minimum size:** stacked lockup 96 px (screen) / 25 mm (print) wide; horizontal lockup 140 px /
  35 mm wide so the Persian name stays legible; emblem alone 24 px / 6 mm. Below 32 px use the
  favicon files, which are tuned for small sizes.

## Do not

Stretch, rotate, recolour outside the palette, add shadows/glows/gradients/outlines, re-type the
name in another font, place on low-contrast backgrounds, or combine with claims such as
"organic", "premium grade" or certification marks that have not been verified.

## Typography

Vazirmatn (SIL Open Font License), regular and bold, for the website, receipts and admin. The
logo name is part of the artwork, not live text.

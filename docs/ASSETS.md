# Image assets

All photographs on the site are **AI-generated illustrations** made for this project. They are not
photos of Fallah & Sons products and must not be presented as what customers will receive. In the
database every generated image is marked `is_generated_sample`, and the storefront labels sample
products. Replace them with real photographs before launch.

Exact generation prompts were not preserved in the repository. The brief for every image was: warm
natural light, cream linen and ceramic props, the brand palette (forest green, harvest gold, cream),
no text, no logos, no packaging claims, no certification marks, no people's faces. The logo concept
prompt is recorded in `fallah-brand-assets/README.md`.

## Manifest

Originals: `fallah-brand-assets/generated/*.jpg`. Web versions (WebP, used by `seed_store`):
`backend/seed/images/*.webp`; the editorial image is also served statically from
`frontend/public/brand/editorial-cooking.webp`.

| File | Size | Subject | Used for | Status |
|---|---|---|---|---|
| `hero-desktop` | 1280×720 | Bowl of white rice with saffron, glass of tea, rice sack, panicles on cream linen | Home hero (desktop crop) | Sample banner |
| `hero-mobile` | 720×1280 | Same scene, portrait | Home hero (mobile crop) | Sample banner |
| `category-rice` | 1152×864 | Green ceramic bowl of long-grain rice with panicles | Rice category | Generated |
| `category-tea` | 1152×864 | Brass teapot, glass of black tea, loose leaves, sugar cubes | Tea category | Generated |
| `category-olive-oil` | 1152×864 | Oil poured into a dish, olives and olive branches | Olive oil category | Generated |
| `editorial-cooking` | 1280×720 | Hands serving rice with tahdig and herbs | Home buying-guide section | Generated |
| `product-rice` | 1024×1024 | Plain cloth sack of rice with wooden scoop | Sample rice product | Sample |
| `product-rice-detail` | 1024×1024 | Raw and cooked long grains with saffron | Sample rice gallery | Sample |
| `product-tea` | 1024×1024 | Green tin, tea glass, loose black tea | Sample tea product | Sample |
| `product-olive-oil` | 1024×1024 | Unlabelled dark glass bottle, olives, dish of oil | Sample olive-oil product | Sample |

Brand files (logo, icons, social image) are listed in [BRAND.md](BRAND.md).

## Replacing images

Everything is managed in the admin; no code change is needed:

- **Product photos:** کاتالوگ محصولات › محصولات › open the product › گالری تصاویر. Upload JPEG/PNG/WebP/AVIF
  (up to 8 MB; at least 1200 px on the long side, square works best), write the alt text, set the
  order; delete the generated rows. The first image is the main one.
- **Categories:** کاتالوگ محصولات › دسته‌بندی‌ها › تصویر (4:3 works best).
- **Home banner:** محتوا و تنظیمات › بنرهای صفحهٔ اصلی; desktop 16:9 and mobile 9:16 images, alt
  text, button text and link. Untick "generated sample" for real photos.
- **Editorial image:** `frontend/public/brand/editorial-cooking.webp` (replace the file and redeploy).

Uploaded images are validated (real image content, allowed format, at most 8 MB) and served through Next's image optimizer
(AVIF/WebP at the right width).

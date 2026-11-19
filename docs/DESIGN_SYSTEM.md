# Design system

Calm, warm and trustworthy: a family food shop, not a discount marketplace. Tokens live in
`frontend/src/app/globals.css` (`@theme`, Tailwind CSS 4); the admin mirrors the palette in
`backend/static/admin/fallah-admin.css`.

## Colour tokens

| Tailwind name | Hex | Use |
|---|---|---|
| `green-800` | `#173F35` | Brand green: header/footer, primary buttons, headings accents |
| `green-950/900/700/600` | `#0C241E` `#10302A` `#1F5546` `#2B6B59` | Hover, pressed, secondary |
| `green-100/50` | `#E3ECE7` `#F0F5F2` | Selected states, soft panels |
| `gold-500` | `#B58A45` | Accents, focus ring, badges. **Never for body text** (contrast 3:1 on rice) |
| `gold-700/600` | `#8A6630` `#9C7638` | Gold text that must pass AA |
| `gold-200/100` | `#E8D6B5` `#F4EAD8` | Selection, highlights |
| `rice` | `#FFFEFA` | Page background |
| `cream`, `cream-200` | `#F6F1E7` `#ECE4D4` | Section bands, cards |
| `line` | `#E2D9C6` | Borders |
| `ink`, `ink-soft`, `ink-muted` | `#202B26` `#4B5650` `#6B746F` | Text levels (all ≥ 4.5:1 on rice) |
| `danger(-soft)`, `success(-soft)`, `warn-soft` | | Errors, confirmations, sample/demo notices |

Shape: card radius 1.25rem, two soft shadows (`card`, `lift`). Containers max 80rem.

## Typography

Vazirmatn variable (self-hosted via `next/font/local`, `--font-vazirmatn`), fallback Tahoma.
Persian digits everywhere customers read numbers (prices, dates, quantities); Latin digits only
inside `dir="ltr"` fragments that customers copy (order numbers, references). Prices: toman with
thousands separators, tabular figures; unit price per kilo/litre shown next to package prices.
Dates: Jalali, Tehran time.

## RTL

- `<html lang="fa" dir="rtl">`; layout uses logical properties (`ms-`, `me-`, `ps-`, `start`,
  `end`, `inline-size`), never left/right.
- Directional icons follow the reading direction: a left chevron means "forward/more", a right
  chevron means "back". Galleries and steppers read right to left.
- Mixed-direction fragments (phone numbers, emails, order numbers, URLs) are wrapped in
  `dir="ltr"` with `unicode-bidi: isolate`.
- Input normalisation on the server accepts Persian/Arabic digits and Arabic ي/ك.

## Responsive

Mobile first, checked at 320, 375, 768, 1024, 1440 and 1920 px. Extra breakpoint `xs` = 360 px
(the header search icon appears from there). Product grids: 1 column → 2 (sm) → 3 (lg) → 4 (xl,
only with more than 3 products, so a small catalog never leaves an empty column). The checkout
summary moves beside the form from `lg`. Hero uses separate mobile (9:16) and desktop (16:9)
crops via `<picture>`. Touch targets ≥ 24 px, primary actions ≥ 44 px.

## Components

Header (demo banner, announcement, logo, category nav, search, account, cart badge, mobile menu
dialog), footer (confirmed contacts, card-safety note), product card (sample badge, sale badge,
price per package and per kilo), buy box (package radios, stock text, quantity stepper), gallery,
breadcrumbs, filters, pagination, empty/error states, FAQ accordion (`details`), order progress,
timeline and totals, toast (`aria-live`).

## Motion

Short (150–250 ms) colour/shadow/transform transitions on hover and focus only; no autoplay
carousels, no parallax. `prefers-reduced-motion` turns transitions off.

## Accessibility rules

One `h1` per page; skip link; visible 3 px gold focus ring; labels on every field, errors tied to
fields with `aria-describedby` plus an error summary; images always have Persian alt text;
status changes announced with `aria-live`; colour is never the only signal (badges have text).

## Content rules

No invented claims: no fake reviews, sales counts, "bestseller" labels, certifications, trust
seals, health claims or urgency timers. Sample products and the mock gateway are labelled as
such wherever they appear.

# Reference Research — Persian Rice / Tea / Olive-Oil Stores

Research for the new store «فلاح و پسران». The two sites below are **inspiration only**. They do not belong to our client, and no identity link is assumed.

## 1. Scope & method

- **Date:** 2026-11-19.
- **Sites:** `https://barekatrice.ir/` ("Barekat") and `https://www.fallah.shop/` ("Fallah.shop").
- **Tool:** `curl` (desktop Chrome user-agent). I parsed the HTML and pulled out visible text, links, meta/OG tags and JSON-LD. Request counts: about 12 for Barekat and 10 for Fallah.shop.
- **Inspected:** homepage, robots.txt, sitemap index, one category/listing page per site (plus Barekat's olive-oil category and Fallah.shop's Tehran and Mashhad pages), one product page (PDP) per site, the empty cart, and the FAQ, about, contact, wholesale and license pages where they exist.
- **Limitations:**
  - Raw HTML only. There was no visual rendering (desktop or mobile), so layout, sticky elements, colours and JS-driven behaviour were not seen.
  - No login, form submission, add-to-cart or checkout, so shipping calculation at checkout and payment flow are **unverified**.
  - Prices are a snapshot from this date.
- **Labels:** "Observed" means it was seen in the fetched HTML. "Inference" means it is my interpretation.

## 2. Per-site findings

### 2.1 Barekat — barekatrice.ir («برنج برکت»)

**Platform (observed):** WordPress 7.1.5, WooCommerce 11.1.2, the WoodMart theme (with a child theme) and Elementor. The sitemap is the WordPress core `wp-sitemap.xml`.

**Navigation & categories (observed):**
- Main menu: خانه, فروشگاه, a categories mega-list, پیگیری سفارش, تأمین عمده برکت, سوالات متداول, درباره ما, تماس با ما, and ورود / ثبت نام.
- Category tree: برنج (برنج ایرانی, آرد برنج), چای (چای ایرانی, چای خارجی, هل), زعفران, روغن زیتون, عسل, قند و نبات.
- The homepage hero slider has three slides (rice, tea, saffron), each with a CTA: «خرید برنج» / «خرید چای» / «خرید زعفران».
- Below the hero: a «پرفروش ترین برنج ها» carousel, a category tile grid, an about teaser, and a blog section.

**Listing (observed):**
- The rice category shows «نمایش همه 8 نتیجه», a per-page selector (9/12/18/24), and a sort dropdown (popularity, rating, newest, cheapest, most expensive).
- Each card shows the name, the price **per kg** («570,000 تومان هر کیلو»), «افزودن به سبد خرید», and «نمای سریع» (quick view).
- Product names put origin first: «برنج هاشمی آستانه اشرفیه (گیلان)», «طارم هاشمی دابودشت فریدونکنار», «عنبربو جنوب شوشتر».

**PDP (observed):**
- The title is followed by the per-kg price, then Description and Additional info tabs. The weight attribute lists «۱۰ کیلوگرم، ۵۰ کیلوگرم، ۱۰۰ کیلوگرم».
- A custom block, «انتخاب اختصاصی محصول — وزن یا تعداد موردنظر را انتخاب کنید», lists each pack (۱۰ کیلوگرمی 5,700,000 / ۵۰ کیلوگرمی 28,500,000 / ۱۰۰ کیلوگرم 57,000,000 تومان) with its own −/+ stepper.
- Under the packs is a live summary: «جمع وزن/تعداد: ۰ کیلوگرم — جمع مبلغ: 0 تومان».
- There is also a generic WooCommerce quantity field, then the add-to-cart button.
- One gallery image. A reviews block with a 5-star histogram shows «هنوز بررسی‌ای ثبت نشده است». Related products are listed under «شاید دوست داشته باشید».

**Non-rice products (observed):** olive oil is sold as separate products per size (250 ml at 677,000 and 700 ml at 1,497,000 تومان). No per-litre price is shown.

**Pricing & currency (observed):** all prices are in **تومان**. JSON-LD has `Offer` + `UnitPriceSpecification`, price 570000, and `priceCurrency: "IRT"`. IRT is not a valid ISO 4217 code; the standard code is IRR.

**Stock (observed):** every product checked showed as in stock, so I saw no out-of-stock state.

**Cart & checkout (observed):**
- The empty cart shows a three-step indicator (سبد خرید → تسویه حساب → سفارش کامل شد) and «بازگشت به فروشگاه».
- Login is by mobile number + OTP («ورود امن با شماره موبایل»); I saw it in the wholesale modal.
- Payment: the FAQ says «درگاه زرین‌پال», and Zarinpal markup appears on the pages.

**Delivery (observed):** the FAQ only says «ارسال به شهرستان‌ها در سریع‌ترین زمان ممکن». **No shipping fee, threshold or lead time is stated** on any page I saw.

**Trust content (observed):**
- An e-Namad page/badge.
- About page: «بیش از ۲۵ سال تجربه», a story that starts from an in-person shop, and values.
- A 15-question FAQ covering hashemi vs. tarom, storage, saffron and payment. It includes a refund promise: «طبق "قول برکت" … هزینه بدون قید و شرط بازگردانده می‌شود».
- A wholesale page (restaurant, catering, hotel, hall) with a lead form and WhatsApp CTA.
- The FAQ says the minimum order is 10 kg («از ۱۰ کیلو … تا ۱۰ تن»).

**Region (observed):** one physical shop in Tehran (Tehranpars). Nationwide shipping is claimed.

**SEO (observed):**
- Title: «برنج برکت – طعم اصیل برنج ایرانی، با اطمینان از کیفیت».
- **No meta description and no OG tags** on the homepage, category or PDP.
- Product JSON-LD is present. Slugs are English (`/product/hashemi-rice-astaneh-ashrafiyeh-cold-cultivated/`).

**Strengths:**
- The per-kg price on cards makes it easy to compare varieties.
- The PDP pack selector shows a running weight and price total.
- Clear category tree, an educational FAQ, a dedicated B2B path, and order tracking.

**Friction (observed):**
- Leftover WoodMart demo content on the homepage: blog posts about furniture and "Atlanta homes" by the author «وودمارت».
- Placeholder social links (`instagram.com/USERNAME`, `wa.me/98XXXXXXXXXX`).
- No shipping cost information anywhere.
- *Inference:* the listing's one-click «افزودن به سبد خرید» on a per-kg product, next to a 10 kg minimum, makes it unclear what gets added. The PDP also has two quantity mechanisms (pack steppers plus a generic qty field), which could confuse buyers.
- Missing meta description and OG tags hurt sharing previews.

### 2.2 Fallah.shop — www.fallah.shop («برنج فلاح و پسران» / «بازرگانی فلاح»)

**Platform (observed):** WordPress + WooCommerce (WooCommerce paths appear in robots.txt), Elementor, Rank Math-style `sitemap_index.xml`, Performance Lab. Uploads live under `/data/uploads/` (a customised path).

> **Important:** the site title is «برنج فلاح و پسران», the same name as our client. We have **not** assumed any relationship. Flag to the client: naming, trademark and SEO-confusion risk, and differentiation (see §5).

**Navigation (observed):**
- The homepage is a city gate, «انتخاب شهر: تهران / مشهد», plus a short history paragraph and «جهت دریافت نمایندگی کلیک کنید».
- Bottom mobile-style nav: خانه, سبد خرید, حساب کاربری, تماس تلفنی.
- **There are no product categories.** Each city page is a flat list of everything in that branch's warehouse («لیست محصولات انبار مشهد»).

**Listing (observed):**
- The Mashhad page has about 30+ rice items, plus non-rice items such as قند and کنسرو in the sitemap (132 product URLs in total).
- Card: name, **package price** («5,950,000 تومان»), and add-to-cart. Out-of-stock items show «اتمام موجودی» with «اطلاعات بیشتر» instead of the cart button; some keep their price, some hide it.
- Mixed packaging shows in names: «(جدید)» / «(کهنه)» (new vs. aged crop), «متقالی», «کیسه آبی», «قوطی 500 گرمی».

**PDP (observed):**
- Single image with zoom («بزرگنمایی تصویر»).
- Long description that includes cultivation timing and a cooking method («طرز پخت: … ۸ الی ۱۵ ساعت … بخیسانید»).
- Attributes «شعبه: مشهد» and «وزن: 10 کیلوگرم», then price, qty («عدد») and add-to-cart.
- The branch's shipping rule is repeated on the PDP.

**Variants & weights (observed):** none. **Every weight is a separate simple product**, sometimes duplicated per city, e.g. the `-mashhad` slugs. No per-kg price is shown.

**Pricing & currency (observed):** the UI shows تومان. JSON-LD `Offer` gives price **59500000 IRR** (rial, ×10) for the item shown as 5,950,000 تومان. *Inference:* this is a correct ISO code, but the toman/rial difference needs care in structured data.

**Delivery & region (observed):**
- Rules differ by city. Mashhad: «ارسال رایگان برای خرید بیش از 18 میلیون تومان» and otherwise «140 هزار تومان».
- Tehran: «هزینه ارسال برای کلیه سفارشات 400 هزار تومان», but also «شعبه تهران: غیر فعال» and «در حال حاضر فروش و ثبت سفارش برای شهر تهران امکان‌پذیر نیست».
- Contact page: Mashhad delivery runs daily from 12 to 15. The Tehran page says «ارسال (روزهای فرد)».

**Ordering & payment (observed):**
- Order channels are listed with hours: website, phone (with hours), and in-person.
- «پرداخت آنلاین با درگاه‌های عضو شتاب» and «پرداخت در محل نداریم».
- Card and IBAN numbers are published for manual transfer, and **they differ between the Tehran page and the contact page**.

**Trust content (observed):**
- A founding story with a historical date and town, plus multiple branch phone lines, a Mashhad address, and a "route to store" link.
- An e-Namad badge on `/license/`.
- No FAQ, returns or terms page was found in the page sitemap: home, contact, mashhad, products, tehran, checkout, license, cart, account.

**SEO (observed):**
- Full OG and Twitter tags, but the homepage meta description is just «برنج». Product OG descriptions are the full product text.
- JSON-LD: WebSite with a SearchAction, and Product/Offer on PDPs.
- Slugs are mixed: English (`iranian-fallah-rice-5star-10kg-mashhad`) and percent-encoded Persian.

**Strengths:**
- Delivery cost and free-shipping threshold are stated up front, on every page.
- City/branch availability is explicit.
- Order, shipping and payment procedures are laid out with working hours.
- Cooking instructions on the PDP.
- A clear out-of-stock label.

**Friction (observed):**
- An **expired Nowruz banner** (orders paused 1403/12/23–1404/01/16) is still shown site-wide.
- Tehran is "inactive" yet still lists products and a fee.
- Conflicting bank details and Tehran delivery info across pages.
- No categories or filters on a list of about 30 items.
- A slug leaked into a product name («…(جدید)کشت-اول5ستاره-کیسه-ابی2-5-کیلویی-جدی»).
- No per-kg comparison.
- Meta description is «برنج».

## 3. Comparison

| Aspect | Barekat | Fallah.shop |
|---|---|---|
| Stack | WooCommerce + WoodMart + Elementor | WooCommerce + Elementor + Rank Math-style sitemap |
| Categories | Tree: rice/tea/saffron/oil/honey/nabat | None; flat list per city |
| Price on card | Per kg («هر کیلو») | Per package |
| Weight choice | One product with 10/50/100 kg pack steppers and a live total | Separate product per weight |
| Stock state | Not observed (all in stock) | «اتمام موجودی», price sometimes hidden |
| Shipping cost | Not stated | Stated per city, with a free threshold |
| Regional | Nationwide claim, Tehran shop | City gate (Tehran inactive, Mashhad active) |
| Payment | Zarinpal | Shetab gateway, no COD, card-to-card details |
| Trust | e-Namad, FAQ, refund promise, about, B2B | e-Namad, history, branches, hours |
| SEO | Product JSON-LD (IRT), no meta/OG | OG + JSON-LD (IRR), weak description |
| Hygiene | Demo blog and placeholder socials | Stale banner, conflicting info |

## 4. Lessons for our store (actionable)

1. **Show both prices.** Make the package price the primary price and show a per-kg (or per-litre for oil) price as secondary, e.g. «۵٬۹۵۰٬۰۰۰ تومان · هر کیلو ۵۹۵٬۰۰۰». Barekat shows only per-kg and Fallah.shop only per-package; each is half the picture.
2. **Model weights as variations of one product**, e.g. 2.5 / 5 / 10 kg rice and 250 / 700 ml oil, with a clear segmented selector. Fallah.shop's one-product-per-weight setup bloats the list.
3. **Use one quantity mechanism.** Barekat's running total is good, but don't combine pack steppers with a second generic qty field. The listing CTA should be «انتخاب وزن» when a weight must be chosen.
4. **State delivery cost and lead time before checkout**: on the PDP, in the cart, and on a dedicated shipping page, including any free-shipping threshold and coverage by region. Fallah.shop does this well; Barekat omits it.
5. **Design clear out-of-stock and "not deliverable to your city" states.** Keep the price visible, disable the CTA, and optionally offer «خبرم کن». Don't list products for an inactive region without a clear notice.
6. **Use a real category tree** (rice by variety/origin, tea, olive oil) with sort and filter options, even for a small catalogue.
7. **Use descriptive product names** (variety + origin + crop year/new-or-aged + weight), and show the new/aged crop as an attribute, not only inside the name.
8. **Educational content sells:** a cooking method on the PDP and an FAQ (hashemi vs. tarom, storage, grain colour, broken grains). Write our own text.
9. **Trust basics:** e-Namad, a real address and phone, a written return policy, payment gateway logos, and order tracking. Publish a single, consistent set of payment details, or better, none (gateway only).
10. **Content hygiene:** remove theme demo content and placeholder links before launch, and give time-bound banners an automatic expiry.
11. **SEO:** a unique meta description for each page, OG tags, and Product JSON-LD with a valid `priceCurrency` (IRR, with the price converted from toman). Use a consistent slug strategy and an XML sitemap.
12. **Optional B2B path** (restaurants, caterers) as a separate lead form, kept apart from the consumer checkout.

## 5. Do not copy

- Their **names, logos, slogans and taglines** (e.g. «اصالت در هر دانه», «عطر شمال، روی سفره شما», «قول برکت»), or their **product names or descriptions**.
- **Images and photography** in any form.
- **Phone numbers, addresses, bank card/IBAN numbers, e-Namad IDs.** These are deliberately not reproduced here.
- **Founding dates and histories** (e.g. Fallah.shop's founding-year story, Barekat's «۲۵+ سال»). Our client's history must come from the client.
- **Policies and figures:** shipping fees, thresholds, minimum order, refund promises, working hours. Our values must be decided by the client.
- **Name overlap:** Fallah.shop trades as «برنج فلاح و پسران» / «بازرگانی فلاح». The client should confirm their right to the name, decide how to differentiate (domain, logo, a tagline that names the person or region), and not imply any affiliation.

## 6. Sources (fetched 2026-11-19)

- Barekat: [home](https://barekatrice.ir/) · [robots.txt](https://barekatrice.ir/robots.txt) · [sitemap](https://barekatrice.ir/wp-sitemap.xml) · [rice category](https://barekatrice.ir/product-category/rice/) · [olive-oil category](https://barekatrice.ir/product-category/olive-oil/) · [PDP: hashemi](https://barekatrice.ir/product/hashemi-rice-astaneh-ashrafiyeh-cold-cultivated/) · [cart](https://barekatrice.ir/cart/) · [FAQ](https://barekatrice.ir/faqs/) · [about](https://barekatrice.ir/about-us/) · [contact](https://barekatrice.ir/contact-us/) · [wholesale](https://barekatrice.ir/wholesale-supply/)
- Fallah.shop: [home](https://www.fallah.shop/) · [robots.txt](https://www.fallah.shop/robots.txt) · [sitemap index](https://www.fallah.shop/sitemap_index.xml) · [page sitemap](https://www.fallah.shop/page-sitemap.xml) · [product sitemap](https://www.fallah.shop/product-sitemap.xml) · [Tehran](https://www.fallah.shop/tehran/) · [Mashhad](https://www.fallah.shop/mashhad/) · [PDP: 5-star 10 kg](https://www.fallah.shop/iranian-fallah-rice-5star-10kg-mashhad/) · [contact](https://www.fallah.shop/contact/) · [license](https://www.fallah.shop/license/) · [cart](https://www.fallah.shop/cart/)

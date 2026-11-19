"""Idempotent seed: creates missing reference data and sample catalog, never overwrites owner edits.

Usage:
    python manage.py seed_store              # reference data + 3 sample products
    python manage.py seed_store --no-samples # reference data only (provinces, categories, pages, shipping, providers)
"""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Category, Product, ProductAttribute, ProductImage, ProductVariant
from apps.core.models import FAQ, HomeBanner, Page, StoreSettings
from apps.payments.models import PaymentProvider
from apps.shipping.models import Province, ShippingMethod, ShippingRate, ShippingZone

SEED_IMAGES = Path(settings.BASE_DIR) / "seed" / "images"

PROVINCES = [
    "تهران", "البرز", "اصفهان", "فارس", "خراسان رضوی", "آذربایجان شرقی", "آذربایجان غربی", "اردبیل",
    "ایلام", "بوشهر", "چهارمحال و بختیاری", "خراسان جنوبی", "خراسان شمالی", "خوزستان", "زنجان", "سمنان",
    "سیستان و بلوچستان", "قزوین", "قم", "کردستان", "کرمان", "کرمانشاه", "کهگیلویه و بویراحمد", "گلستان",
    "گیلان", "لرستان", "مازندران", "مرکزی", "هرمزگان", "همدان", "یزد",
]  # fmt: skip

CATEGORIES = [
    {
        "slug": "rice",
        "name": "برنج",
        "description": "برنج ایرانی در بسته‌های خانوادگی؛ قیمت هر بسته و قیمت هر کیلو را کنار هم ببینید.",
        "image": "category-rice.webp",
        "image_alt": "دانه‌های برنج سفید در کاسهٔ سفالی کنار خوشهٔ برنج",
        "sort_order": 1,
    },
    {
        "slug": "tea",
        "name": "چای",
        "description": "چای سیاه برای دم‌کردن روزانه.",
        "image": "category-tea.webp",
        "image_alt": "استکان چای کنار قوری و برگ‌های خشک چای",
        "sort_order": 2,
    },
    {
        "slug": "olive-oil",
        "name": "روغن زیتون",
        "description": "روغن زیتون در بطری‌های شیشه‌ای.",
        "image": "category-olive-oil.webp",
        "image_alt": "بطری شیشه‌ای روغن زیتون کنار زیتون سبز",
        "sort_order": 3,
    },
]

SAMPLE_NOTE = (
    "این محصول نمونهٔ نمایشی است؛ قیمت، موجودی و تصویر آن آزمایشی است و پیش از فروش واقعی باید توسط مالک تأیید شود."
)

PRODUCTS = [
    {
        "slug": "iranian-long-grain-rice",
        "sku": "FS-RICE-01",
        "category": "rice",
        "name": "برنج ایرانی دانه‌بلند",
        "short_description": "برنج سفید دانه‌بلند برای کته و پلو؛ در دو بستهٔ خانوادگی.",
        "description": (
            "برنج سفید دانه‌بلند ایرانی برای پخت روزانه و مهمانی.\n\n"
            "رقم، منطقهٔ کشت و سال برداشت این بسته پس از تأیید مالک درج می‌شود.\n\n" + SAMPLE_NOTE
        ),
        "storage_and_use": (
            "## نگهداری\nدر ظرف دربسته، در جای خشک، خنک و دور از نور مستقیم نگهداری کنید.\n\n"
            "## راهنمای کلی پخت آبکش\nبرنج را چند بار بشویید تا آب آن شفاف شود و حدود دو ساعت در آب و کمی نمک خیس کنید. "
            "در آب جوش بریزید و وقتی دانه‌ها نرم شدند اما مغزشان هنوز کمی سفت بود، آبکش کنید. "
            "سپس با کمی روغن و آب، با حرارت ملایم و درِ دم‌کنی‌دار دم بگذارید.\n\n"
            "زمان خیساندن و پخت به رقم و کهنگی برنج بستگی دارد؛ اولین بار با مقدار کم امتحان کنید."
        ),
        "is_featured": True,
        "sort_order": 1,
        "images": [
            ("product-rice.webp", "کیسهٔ پارچه‌ای برنج کنار کاسهٔ دانه‌های برنج سفید"),
            ("product-rice-detail.webp", "نمای نزدیک دانه‌های بلند برنج سفید"),
        ],
        "attributes": [("نوع", "برنج سفید دانه‌بلند"), ("فروش", "بسته‌بندی‌شده؛ فقط بستهٔ کامل")],
        "variants": [
            {"sku": "FS-RICE-01-5", "title": "کیسهٔ ۵ کیلوگرمی", "amount": "5", "unit": "kg",
             "price_toman": 1_750_000, "sale_toman": None, "stock": 25, "weight": 5_150},
            {"sku": "FS-RICE-01-10", "title": "کیسهٔ ۱۰ کیلوگرمی", "amount": "10", "unit": "kg",
             "price_toman": 3_400_000, "sale_toman": 3_290_000, "stock": 12, "weight": 10_250},
        ],
    },
    {
        "slug": "iranian-black-tea",
        "sku": "FS-TEA-01",
        "category": "tea",
        "name": "چای سیاه ایرانی",
        "short_description": "چای سیاه برگ برای دم‌کردن روزانه.",
        "description": "چای سیاه برگ برای دم‌کردن در قوری.\n\nمنطقهٔ تولید و فصل برداشت پس از تأیید مالک درج می‌شود.\n\n"
        + SAMPLE_NOTE,
        "storage_and_use": (
            "## نگهداری\nدر ظرف دربسته و دور از رطوبت، نور و بوهای تند نگهداری کنید.\n\n"
            "## دم‌کردن\nبرای هر استکان حدود یک قاشق چای‌خوری چای در قوری گرم بریزید، آب جوش اضافه کنید "
            "و چند دقیقه روی حرارت ملایم دم بگذارید."
        ),
        "is_featured": True,
        "sort_order": 2,
        "images": [("product-tea.webp", "بستهٔ چای و استکان چای روی سینی")],
        "attributes": [("نوع", "چای سیاه برگ")],
        "variants": [
            {"sku": "FS-TEA-01-500", "title": "بستهٔ ۵۰۰ گرمی", "amount": "500", "unit": "g",
             "price_toman": 420_000, "sale_toman": None, "stock": 30, "weight": 600},
            {"sku": "FS-TEA-01-1000", "title": "بستهٔ ۱ کیلوگرمی", "amount": "1", "unit": "kg",
             "price_toman": 810_000, "sale_toman": None, "stock": 4, "weight": 1_150},
        ],
    },
    {
        "slug": "olive-oil",
        "sku": "FS-OIL-01",
        "category": "olive-oil",
        "name": "روغن زیتون",
        "short_description": "روغن زیتون در بطری شیشه‌ای.",
        "description": "روغن زیتون در بطری شیشه‌ای.\n\nنوع روغن، منشأ و تاریخ تولید پس از تأیید مالک درج می‌شود.\n\n"
        + SAMPLE_NOTE,
        "storage_and_use": "## نگهداری\nدرِ بطری را پس از مصرف ببندید و در جای خنک و دور از نور نگهداری کنید.",
        "is_featured": True,
        "sort_order": 3,
        "images": [("product-olive-oil.webp", "بطری شیشه‌ای روغن زیتون کنار زیتون")],
        "attributes": [],
        "variants": [
            {"sku": "FS-OIL-01-500", "title": "بطری ۵۰۰ میلی‌لیتری", "amount": "500", "unit": "ml",
             "price_toman": 650_000, "sale_toman": None, "stock": 20, "weight": 950},
            {"sku": "FS-OIL-01-1000", "title": "بطری ۱ لیتری", "amount": "1", "unit": "l",
             "price_toman": 1_200_000, "sale_toman": None, "stock": 0, "weight": 1_650},
        ],
    },
]  # fmt: skip

POLICY_NOTICE = "این متن پیش‌نویس است و پس از تأیید مالک فروشگاه نهایی می‌شود."

PAGES = [
    {
        "slug": "about",
        "title": "دربارهٔ فلاح و پسران",
        "summary": "فروشگاه آنلاین برنج ایرانی، چای و روغن زیتون.",
        "body": (
            "فلاح و پسران فروشگاه آنلاین برنج ایرانی و چند خوراکی برگزیده برای سفرهٔ خانواده است.\n\n"
            "## آنچه در این فروشگاه می‌بینید\n"
            "قیمت هر بسته و قیمت هر کیلو را کنار هم می‌بینید، هزینهٔ ارسال پیش از پرداخت مشخص است "
            "و وضعیت سفارش را با شمارهٔ سفارش پیگیری می‌کنید.\n\n"
            "## تماس\nبرای پرسش دربارهٔ محصولات یا سفارش از صفحهٔ تماس با ما با ما در ارتباط باشید."
        ),
    },
    {
        "slug": "shipping",
        "title": "شیوه‌های ارسال",
        "summary": "روش‌های ارسال و نحوهٔ محاسبهٔ هزینه.",
        "body": (
            POLICY_NOTICE + "\n\n"
            "## محاسبهٔ هزینه\nهزینهٔ ارسال بر اساس استان و شهر مقصد، روش ارسال و وزن بسته‌ها محاسبه می‌شود "
            "و پیش از پرداخت در صفحهٔ تکمیل خرید نمایش داده می‌شود.\n\n"
            "## پس‌کرایه\nدر روش‌هایی که پس‌کرایه هستند، هزینهٔ ارسال هنگام تحویل به شرکت حمل پرداخت می‌شود "
            "و در مبلغ پرداخت آنلاین حساب نمی‌شود.\n\n"
            "## زمان ارسال\nزمان آماده‌سازی و تحویل پس از تأیید مالک در این صفحه درج می‌شود."
        ),
    },
    {
        "slug": "returns",
        "title": "شرایط لغو و مرجوعی",
        "summary": "لغو سفارش، مرجوعی و بازگشت وجه.",
        "body": (
            POLICY_NOTICE + "\n\n"
            "## لغو پیش از ارسال\nتا پیش از تحویل سفارش به حمل‌کننده، برای لغو با ما تماس بگیرید.\n\n"
            "## کالای آسیب‌دیده یا مغایر\nاگر بسته آسیب‌دیده یا مغایر با سفارش بود، همان روز تحویل با شمارهٔ سفارش "
            "و عکس بسته با ما تماس بگیرید.\n\n"
            "## بازگشت وجه\nبازگشت وجه پس از بررسی و از همان مسیر پرداخت یا روشی که مالک اعلام می‌کند انجام می‌شود."
        ),
    },
    {
        "slug": "privacy",
        "title": "حریم خصوصی",
        "summary": "اطلاعاتی که برای ثبت و ارسال سفارش لازم است.",
        "body": (
            POLICY_NOTICE + "\n\n"
            "## اطلاعات دریافتی\nنام، شمارهٔ همراه و نشانی فقط برای ثبت، ارسال و پیگیری سفارش استفاده می‌شود.\n\n"
            "## اطلاعات کارت\nاطلاعات کارت بانکی، رمز دوم یا CVV2 در این فروشگاه وارد یا ذخیره نمی‌شود؛ "
            "پرداخت در صفحهٔ درگاه بانکی انجام می‌شود."
        ),
    },
    {
        "slug": "terms",
        "title": "قوانین خرید",
        "summary": "قیمت‌ها، پرداخت و ثبت سفارش.",
        "body": (
            POLICY_NOTICE + "\n\n"
            "## قیمت‌ها\nقیمت‌ها به تومان نمایش داده می‌شوند و مبلغ نهایی پیش از پرداخت در خلاصهٔ سفارش آمده است.\n\n"
            "## ثبت سفارش\nسفارش پس از تأیید پرداخت توسط درگاه بانکی قطعی می‌شود. "
            "موجودی تا پایان مهلت پرداخت برای شما رزرو می‌ماند."
        ),
    },
]

FAQS = [
    ("قیمت‌ها به چه واحدی است؟", "همهٔ قیمت‌های سایت به تومان است. مبلغی که در درگاه بانکی می‌بینید ممکن است به ریال (ده برابر) نمایش داده شود.", "خرید"),
    ("قیمت هر کیلو برای چیست؟", "برای مقایسهٔ بسته‌های مختلف است. مبلغ قابل پرداخت همیشه قیمت هر بسته ضرب در تعداد است.", "خرید"),
    ("هزینهٔ ارسال چطور محاسبه می‌شود؟", "بر اساس استان و شهر مقصد، روش ارسال و وزن بسته‌ها. پیش از پرداخت در صفحهٔ تکمیل خرید نمایش داده می‌شود.", "ارسال"),
    ("برای خرید باید ثبت‌نام کنم؟", "خیر. می‌توانید بدون ورود خرید کنید. با ورود از طریق شمارهٔ همراه، سفارش‌ها و نشانی‌هایتان ذخیره می‌شود.", "خرید"),
    ("سفارشم را چطور پیگیری کنم؟", "در صفحهٔ پیگیری سفارش، شمارهٔ سفارش و شمارهٔ همراهی را که هنگام خرید وارد کردید بنویسید.", "سفارش"),
    ("اگر پرداخت ناموفق شد چه کنم؟", "اگر مبلغی از حساب شما کم نشده، از صفحهٔ سفارش دوباره پرداخت کنید. اگر مبلغ کم شده ولی سفارش تأیید نشده، دوباره پرداخت نکنید و با شمارهٔ سفارش با ما تماس بگیرید.", "پرداخت"),
]  # fmt: skip

PROVIDERS = [
    ("MOCK", "درگاه آزمایشی", "فقط محیط توسعه؛ پولی جابه‌جا نمی‌شود.", 0),
    ("ZARINPAL", "زرین‌پال", "پرداخت با همهٔ کارت‌های عضو شتاب", 1),
    ("ZIBAL", "زیبال", "پرداخت با همهٔ کارت‌های عضو شتاب", 2),
    ("SEP", "سامان (سپ)", "پرداخت با همهٔ کارت‌های عضو شتاب", 3),
    ("MELLAT", "بانک ملت (به‌پرداخت)", "پرداخت با همهٔ کارت‌های عضو شتاب", 4),
    ("BMI", "بانک ملی (سداد)", "پرداخت با همهٔ کارت‌های عضو شتاب", 5),
]


def rial(toman: int | None) -> int | None:
    return None if toman is None else toman * 10


class Command(BaseCommand):
    help = "ایجاد داده‌های پایه و محصولات نمونه (بدون بازنویسی داده‌های موجود)."

    def add_arguments(self, parser):
        parser.add_argument("--no-samples", action="store_true", help="محصولات و بنر نمونه ساخته نشود.")

    def handle(self, *args, no_samples: bool = False, **options):
        if settings.IS_PRODUCTION and not no_samples:
            raise CommandError("در محیط تولید فقط با --no-samples اجرا کنید.")
        self.created: list[str] = []
        with transaction.atomic():
            StoreSettings.load()
            self.seed_provinces()
            categories = self.seed_categories()
            self.seed_pages()
            self.seed_faqs()
            self.seed_shipping()
            self.seed_providers()
            if not no_samples:
                self.seed_products(categories)
                self.seed_banner()
        if self.created:
            for line in self.created:
                self.stdout.write(f"  + {line}")
        self.stdout.write(self.style.SUCCESS(f"seed_store: {len(self.created)} مورد جدید ساخته شد."))

    def _image(self, field, filename: str) -> None:
        path = SEED_IMAGES / filename
        if not path.exists():
            raise CommandError(f"تصویر نمونه پیدا نشد: {path}")
        with path.open("rb") as fh:
            field.save(filename, File(fh), save=False)

    def seed_provinces(self):
        for index, name in enumerate(PROVINCES):
            _, created = Province.objects.get_or_create(name=name, defaults={"sort_order": index})
            if created:
                self.created.append(f"استان {name}")

    def seed_categories(self) -> dict[str, Category]:
        result = {}
        for spec in CATEGORIES:
            category = Category.objects.filter(slug=spec["slug"]).first()
            if category is None:
                category = Category(
                    slug=spec["slug"],
                    name=spec["name"],
                    description=spec["description"],
                    image_alt=spec["image_alt"],
                    sort_order=spec["sort_order"],
                    show_when_empty=True,
                )
                self._image(category.image, spec["image"])
                category.save()
                self.created.append(f"دسته {category.name}")
            result[spec["slug"]] = category
        return result

    def seed_pages(self):
        for spec in PAGES:
            _, created = Page.objects.get_or_create(slug=spec["slug"], defaults={**spec, "requires_owner_review": True})
            if created:
                self.created.append(f"صفحه {spec['title']}")

    def seed_faqs(self):
        for index, (question, answer, group) in enumerate(FAQS):
            _, created = FAQ.objects.get_or_create(
                question=question, defaults={"answer": answer, "group": group, "sort_order": index}
            )
            if created:
                self.created.append(f"پرسش {question}")

    def seed_shipping(self):
        provinces = list(Province.objects.all())
        tehran = Province.objects.get(name="تهران")
        nationwide, created = ShippingZone.objects.get_or_create(name="سراسر کشور")
        if created:
            nationwide.provinces.set(provinces)
            self.created.append("منطقه سراسر کشور")
        tehran_city, created = ShippingZone.objects.get_or_create(name="شهر تهران", defaults={"city_names": "تهران"})
        if created:
            tehran_city.provinces.set([tehran])
            self.created.append("منطقه شهر تهران")

        methods = [
            (
                {"code": "post", "name": "پست پیشتاز", "kind": ShippingMethod.Kind.POST, "sort_order": 1,
                 "description": "ارسال به سراسر کشور با پست.", "max_weight_grams": 30_000},
                [(nationwide, 900_000, 2_000, 250_000, 50_000_000)],
            ),
            (
                {"code": "tehran-courier", "name": "پیک تهران", "kind": ShippingMethod.Kind.COURIER, "sort_order": 2,
                 "description": "ارسال با پیک در شهر تهران.", "max_weight_grams": 40_000},
                [(tehran_city, 1_200_000, 40_000, 0, None)],
            ),
            (
                {"code": "freight-cod", "name": "باربری (پس‌کرایه)", "kind": ShippingMethod.Kind.FREIGHT,
                 "sort_order": 3, "payment_timing": ShippingMethod.PaymentTiming.ON_DELIVERY,
                 "description": "برای سفارش‌های سنگین؛ هزینهٔ حمل هنگام تحویل به باربری پرداخت می‌شود.",
                 "min_weight_grams": 20_000},
                [(nationwide, 0, 0, 0, None)],
            ),
        ]  # fmt: skip
        for defaults, rates in methods:
            method, created = ShippingMethod.objects.get_or_create(code=defaults["code"], defaults=defaults)
            if created:
                self.created.append(f"روش ارسال {method.name}")
                for zone, base, included, per_kg, free in rates:
                    ShippingRate.objects.create(
                        method=method,
                        zone=zone,
                        base_cost=base,
                        included_weight_grams=included,
                        per_extra_kg_cost=per_kg,
                        free_shipping_threshold=free,
                    )

    def seed_providers(self):
        has_default = PaymentProvider.objects.filter(is_default=True).exists()
        for code, name, description, order in PROVIDERS:
            if code == "MOCK" and not settings.PAYMENT_MOCK_ENABLED:
                continue
            enabled = code == "MOCK"
            _, created = PaymentProvider.objects.get_or_create(
                code=code,
                defaults={
                    "display_name": name,
                    "description": description,
                    "is_enabled": enabled,
                    "is_default": enabled and not has_default,
                    "sort_order": order,
                },
            )
            if created:
                has_default = has_default or enabled
                self.created.append(f"درگاه {name}")

    def seed_products(self, categories: dict[str, Category]):
        created_products = []
        for spec in PRODUCTS:
            if Product.objects.filter(slug=spec["slug"]).exists():
                continue
            product = Product.objects.create(
                slug=spec["slug"],
                sku=spec["sku"],
                category=categories[spec["category"]],
                name=spec["name"],
                short_description=spec["short_description"],
                description=spec["description"],
                storage_and_use=spec["storage_and_use"],
                is_featured=spec["is_featured"],
                is_sample=True,
                status=Product.Status.PUBLISHED,
                sort_order=spec["sort_order"],
            )
            for index, (filename, alt) in enumerate(spec["images"]):
                image = ProductImage(product=product, alt_text=alt, sort_order=index, is_generated_sample=True)
                self._image(image.image, filename)
                image.save()
            for index, (name, value) in enumerate(spec["attributes"]):
                ProductAttribute.objects.create(product=product, name=name, value=value, sort_order=index)
            for index, variant in enumerate(spec["variants"]):
                ProductVariant.objects.create(
                    product=product,
                    sku=variant["sku"],
                    title=variant["title"],
                    package_amount=Decimal(variant["amount"]),
                    package_unit=variant["unit"],
                    price=rial(variant["price_toman"]),
                    sale_price=rial(variant["sale_toman"]),
                    stock=variant["stock"],
                    shipping_weight_grams=variant["weight"],
                    sort_order=index,
                )
            created_products.append(product)
            self.created.append(f"محصول نمونه {product.name}")
        if created_products:
            every = list(Product.objects.filter(is_sample=True))
            for product in every:
                product.related_products.add(*[p for p in every if p.pk != product.pk])

    def seed_banner(self):
        if HomeBanner.objects.exists():
            return
        banner = HomeBanner(
            eyebrow="فلاح و پسران",
            title="برنج ایرانی برای سفرهٔ هر روز خانواده",
            subtitle="بستهٔ مناسب را انتخاب کنید، قیمت هر کیلو را ببینید و هزینهٔ ارسال را پیش از پرداخت بدانید.",
            image_alt="دیس برنج سفید کنار کیسهٔ برنج و خوشه‌های طلایی برنج",
            cta_label="خرید برنج",
            cta_url="/category/rice",
            is_generated_sample=True,
        )
        self._image(banner.image_desktop, "hero-desktop.webp")
        self._image(banner.image_mobile, "hero-mobile.webp")
        banner.save()
        self.created.append("بنر صفحهٔ اصلی")

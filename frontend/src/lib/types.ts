export type StockStatus = "in_stock" | "low_stock" | "out_of_stock" | "unavailable";

export interface ImageRef {
  url: string;
  alt: string;
  is_generated_sample?: boolean;
}

export interface StoreInfo {
  name: string;
  tagline: string;
  phone: string;
  email: string;
  telegram_username: string;
  address: string;
  business_hours: string;
  announcement: string;
  sales_enabled: boolean;
  seo_title: string;
  seo_description: string;
}

export interface NavCategory {
  name: string;
  slug: string;
  product_count: number;
}

export interface PageLink {
  slug: string;
  title: string;
}

export interface SiteData {
  store: StoreInfo;
  navigation: NavCategory[];
  pages: PageLink[];
  demo_mode: boolean;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  image: string | null;
  image_alt: string;
  product_count: number;
  seo_title?: string;
  seo_description?: string;
  updated_at?: string;
}

export interface UnitPrice {
  label: string;
  amount: number;
}

export interface PriceFrom {
  price: number;
  list_price: number;
  on_sale: boolean;
  variant_title: string;
  unit_price: UnitPrice | null;
}

export interface ProductCard {
  id: number;
  name: string;
  slug: string;
  category: { name: string; slug: string };
  short_description: string;
  is_sample: boolean;
  image: ImageRef | null;
  price_from: PriceFrom | null;
  in_stock: boolean;
  variant_count: number;
  updated_at?: string;
}

export interface Variant {
  id: number;
  title: string;
  sku: string;
  package_amount: string;
  package_unit: string;
  unit_label: string;
  price: number;
  list_price: number;
  on_sale: boolean;
  sale_ends_at: string | null;
  unit_price: UnitPrice | null;
  stock_status: StockStatus;
  low_stock_count: number | null;
  max_quantity: number;
  shipping_weight_grams: number;
}

export interface ProductDetail extends ProductCard {
  sku: string;
  purchasable: boolean;
  updated_at: string;
  description: string;
  storage_and_use: string;
  images: ImageRef[];
  attributes: { name: string; value: string }[];
  variants: Variant[];
  related: ProductCard[];
  seo_title: string;
  seo_description: string;
}

export interface Paginated<T> {
  count: number;
  page: number;
  page_count: number;
  page_size: number;
  results: T[];
}

export interface Banner {
  title: string;
  subtitle: string;
  eyebrow: string;
  image_desktop: string;
  image_mobile: string | null;
  image_alt: string;
  cta_label: string;
  cta_url: string;
  is_generated_sample: boolean;
}

export interface Faq {
  id?: number;
  question: string;
  answer: string;
  group: string;
}

export interface HomeData {
  banners: Banner[];
  categories: Category[];
  featured: ProductCard[];
  faqs: Faq[];
}

export interface ContentPage {
  slug: string;
  title: string;
  summary: string;
  body: string;
  requires_owner_review: boolean;
  seo_title: string;
  seo_description: string;
  updated_at: string;
}

export interface CartLine {
  variant_id: number;
  product_name: string;
  product_slug: string;
  variant_title: string;
  sku: string;
  image: ImageRef | null;
  quantity: number;
  unit_price: number;
  list_unit_price: number;
  line_total: number;
  stock_status: StockStatus;
  max_quantity: number;
  issue: string;
  issue_code: string;
  price_changed_from: number | null;
  is_sample: boolean;
}

export interface Cart {
  lines: CartLine[];
  item_count: number;
  merchandise_total: number;
  discount_total: number;
  subtotal: number;
  weight_grams: number;
  has_issues: boolean;
}

export interface Totals {
  merchandise_total: number;
  discount_total: number;
  tax_total: number;
  shipping_total: number;
  grand_total: number;
}

export interface ShippingOption {
  id: number;
  name: string;
  kind: string;
  description: string;
  delivery_estimate: string;
  requires_address: boolean;
  available: boolean;
  unavailable_reason: string;
  cost: number;
  is_free: boolean;
  pay_on_delivery: boolean;
  free_threshold: number | null;
  totals: Totals;
}

export interface Quote {
  cart: Cart;
  shipping_options: ShippingOption[];
  sales_enabled: boolean;
}

export interface Province {
  id: number;
  name: string;
}

export interface PaymentProviderInfo {
  code: string;
  name: string;
  description: string;
  is_default: boolean;
  is_test: boolean;
}

export interface OrderItem {
  product_name: string;
  variant_title: string;
  sku: string;
  quantity: number;
  unit_price: number;
  list_unit_price: number;
  line_total: number;
}

export interface OrderEvent {
  created_at: string;
  message: string;
}

export interface Shipment {
  status: string;
  status_label: string;
  carrier: string;
  tracking_code: string;
  tracking_url: string;
  shipped_at: string | null;
  delivered_at: string | null;
}

export type OrderStage =
  | "awaiting_payment"
  | "under_review"
  | "unfulfilled"
  | "preparing"
  | "shipped"
  | "delivered"
  | "canceled"
  | "expired"
  | "returned";

export interface OrderPublic {
  number: string;
  created_at: string;
  stage: OrderStage;
  status: string;
  status_label: string;
  payment_status: string;
  payment_status_label: string;
  fulfillment_status: string;
  fulfillment_status_label: string;
  items: OrderItem[];
  shipments: Shipment[];
  shipping_method_name: string;
  shipping_on_delivery: boolean;
  shipping_estimate: string;
  events: OrderEvent[];
}

export interface OrderPrivate extends OrderPublic {
  full_name: string;
  phone: string;
  province_name: string;
  city: string;
  address_line: string;
  postal_code: string;
  merchandise_total: number;
  discount_total: number;
  tax_total: number;
  shipping_total: number;
  grand_total: number;
  currency: string;
  paid_at: string | null;
  reservation_expires_at: string;
  can_pay: boolean;
  is_test: boolean;
  invoice_number: string | null;
  latest_payment: {
    status: string;
    status_label: string;
    provider: string;
    reference_number: string;
    created_at: string;
  } | null;
}

export interface AccountOrderSummary {
  number: string;
  created_at: string;
  grand_total: number;
  status_label: string;
  fulfillment_status_label: string;
  stage?: OrderStage;
}

export interface Address {
  id: number;
  label: string;
  full_name: string;
  phone: string;
  province_id: number;
  province_name: string;
  city: string;
  address_line: string;
  postal_code: string;
  is_default: boolean;
}

export interface ApiErrorBody {
  error: { code: string; message: string; fields: Record<string, unknown> };
}

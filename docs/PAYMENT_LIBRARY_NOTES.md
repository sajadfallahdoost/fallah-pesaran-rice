# Research: `az-iranian-bank-gateways` (Django payment gateway library)

Researched 2026-11-19. Source read from the **PyPI wheel `az_iranian_bank_gateways-2.3.4-py3-none-any.whl`**
(identical to GitHub `master` @ `481a8fc`, except `__init__.__version__`). All paths below are relative to the
installed package `azbankgateways/`. Line numbers refer to 2.3.4.

---

## 1. Package facts

| Item | Value |
|---|---|
| PyPI name / import name | `az-iranian-bank-gateways` / `azbankgateways` |
| Latest version | **2.3.4** (`__init__.py`: `__version__ = "v2.3.4"`) |
| Release date | **2026-01-07** (wheel upload 12:37 UTC) |
| Previous | 2.3.3, 2.3.2, 2.3.1, 2.3.0, 2.2.0 ... |
| License | **MIT** – the shipped `LICENSE` file (wheel `dist-info/licenses/LICENSE`) and README say MIT, "Copyright (c) 2020 Ali Zahedi Gol". **Metadata classifier says "BSD License"** (setup.cfg `license = BSD License`) – inconsistent; treat the LICENSE text (MIT) as authoritative. MIT requires keeping the copyright + permission notice in copies/substantial portions (e.g. a THIRD_PARTY_NOTICES entry). |
| Python | `python_requires >=3.8`; classifiers 3.8–3.12. Tested here on **3.12.3**. |
| Django | `Django>=3.0` (no upper bound). Migration 0006 was generated with Django 6.0.1. No Django classifiers. |
| Dependencies | `six`, `Django>=3.0`, `pycryptodome>=3.9.7` (BMI DES3), `zeep` (Mellat SOAP). `requests` is imported by most banks but **not declared** — it arrives transitively via `zeep`. Pin `requests` explicitly in your project. |
| Tests in repo | None (no test suite in repo or wheel). |

Changes in 2.3.x worth knowing: **IDPay and Pay.ir (PAYV1) were removed** (commits `35cf1a8`, `4fefc4e`: "These two payment systems have stopped operating"); `default_app_config` only set for Django < 3.2.

---

## 2. Installation & settings

### INSTALLED_APPS

```python
INSTALLED_APPS = [..., "azbankgateways", ...]
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"   # MANDATORY for BMI and SEP (see below)
```

`apps.py`: `AZIranianBankGatewaysConfig(name="azbankgateways", default_auto_field="django.db.models.AutoField")`
— the library's `Bank` table uses a 32-bit `AutoField` regardless of your `DEFAULT_AUTO_FIELD`.

BMI and SEP raise in `__init__` if the referrer policy is wrong (`banks/bmi.py:25`, `banks/sep.py:184`):

```python
if not self._is_strict_origin_policy_enabled():   # django_settings.SECURE_REFERRER_POLICY == 'strict-origin-when-cross-origin'
    raise SettingDoesNotExist("SECURE_REFERRER_POLICY is not set to ...")
```

### Settings are read ONCE at import time (`default_settings.py`)

```python
_AZ_IRANIAN_BANK_GATEWAYS = getattr(settings, "AZ_IRANIAN_BANK_GATEWAYS", {})
BANK_PRIORITIES = _AZ.get("BANK_PRIORITIES", [])
BANK_GATEWAYS   = _AZ.get("GATEWAYS", {})
BANK_DEFAULT    = _AZ.get("DEFAULT", "BMI")
BANK_TIMEOUT    = _AZ.get("BANK_TIMEOUT", 5)            # seconds, used for requests/zeep
SETTING_VALUE_READER_CLASS = _AZ.get("SETTING_VALUE_READER_CLASS", "azbankgateways.readers.DefaultReader")
CURRENCY        = _AZ.get("CURRENCY", "IRR")            # your app's currency: "IRR" or "IRT"
TRACKING_CODE_QUERY_PARAM = _AZ.get("TRACKING_CODE_QUERY_PARAM", "tc")
TRACKING_CODE_LENGTH      = _AZ.get("TRACKING_CODE_LENGTH", 16)
IS_SAMPLE_FORM_ENABLE     = _AZ.get("IS_SAMPLE_FORM_ENABLE", False)
IS_SAFE_GET_GATEWAY_PAYMENT = _AZ.get("IS_SAFE_GET_GATEWAY_PAYMENT", False)
CUSTOM_APP      = _AZ.get("CUSTOM_APP")
if CUSTOM_APP:
    CALLBACK_NAMESPACE           = f"{CUSTOM_APP}:azbankgateways:callback"
    GO_TO_BANK_GATEWAY_NAMESPACE = f"{CUSTOM_APP}:azbankgateways:go-to-bank-gateway"
    SAMPLE_RESULT_NAMESPACE      = f"{CUSTOM_APP}:azbankgateways:sample-result"
else:
    CALLBACK_NAMESPACE           = _AZ.get("CALLBACK_NAMESPACE", "azbankgateways:callback")
    GO_TO_BANK_GATEWAY_NAMESPACE = _AZ.get("GO_TO_BANK_GATEWAY_NAMESPACE", "azbankgateways:go-to-bank-gateway")
    SAMPLE_RESULT_NAMESPACE      = _AZ.get("SAMPLE_RESULT_NAMESPACE", "azbankgateways:sample-result")
# Bank class map comes from a TOP-LEVEL Django setting named `CLASS` (not inside the dict!):
BANK_CLASS = getattr(settings, "CLASS", {"BMI": "azbankgateways.banks.BMI", "SEP": ..., "ZARINPAL": ...,
    "ZIBAL": ..., "BAHAMTA": ..., "MELLAT": ..., "IRANDARGAH": "azbankgateways.banks.irandargah.IranDargah",
    "ASANPARDAKHT": "azbankgateways.banks.asanpardakht.AsanPardakht"})
```

Consequences:
* `override_settings(AZ_IRANIAN_BANK_GATEWAYS=...)` in tests has **no effect** after first import — patch
  `azbankgateways.default_settings.<NAME>` instead (or set the dict before Django setup).
* **There is no global `IS_SANDBOX` key.** Sandbox is per-gateway `"SANDBOX": 0|1` and only exists for
  ZARINPAL and IRANDARGAH. There is no `IS_SAFE_GET_GATEWAY` key; the real name is `IS_SAFE_GET_GATEWAY_PAYMENT`.
* `BANK_PRIORITIES` only matters for `auto_create()`; order = `[DEFAULT] + BANK_PRIORITIES` (dedup).

### Full settings dict shape

```python
AZ_IRANIAN_BANK_GATEWAYS = {
    "GATEWAYS": {
        "BMI":          {"MERCHANT_CODE": "...", "TERMINAL_CODE": "...", "SECRET_KEY": "<base64 3DES key>"},
        "SEP":          {"MERCHANT_CODE": "...", "TERMINAL_CODE": "..."},   # NB: SEP sends MERCHANT_CODE as TerminalId
        "ZARINPAL":     {"MERCHANT_CODE": "<uuid>", "SANDBOX": 0},          # SANDBOX optional (default 0)
        "ZIBAL":        {"MERCHANT_CODE": "..."},                           # "zibal" = Zibal's test merchant
        "BAHAMTA":      {"MERCHANT_CODE": "<api_key>"},
        "MELLAT":       {"TERMINAL_CODE": "...", "USERNAME": "...", "PASSWORD": "..."},
        "IRANDARGAH":   {"MERCHANT_CODE": "...", "SANDBOX": 0},
        "ASANPARDAKHT": {"MERCHANT_CONFIGURATION_ID": "...", "USERNAME": "...", "PASSWORD": "..."},
    },
    "DEFAULT": "ZARINPAL",                 # default "BMI" if omitted
    "CURRENCY": "IRR",                     # "IRR" | "IRT" — currency of amounts YOU pass to set_amount()
    "BANK_TIMEOUT": 5,
    "TRACKING_CODE_QUERY_PARAM": "tc",
    "TRACKING_CODE_LENGTH": 16,            # BMI errors at 20
    "SETTING_VALUE_READER_CLASS": "azbankgateways.readers.DefaultReader",
    "BANK_PRIORITIES": [],                 # for auto_create()
    "IS_SAMPLE_FORM_ENABLE": False,        # True exposes /sample-payment/ & /sample-result/ — keep False in prod
    "IS_SAFE_GET_GATEWAY_PAYMENT": True,   # RECOMMENDED: removes the go-to-bank-gateway URL (see §9)
    "CUSTOM_APP": None,                    # e.g. "api:payment" when the include is nested in another namespace
    # "CALLBACK_NAMESPACE": "azbankgateways:callback",                  # ignored if CUSTOM_APP set
    # "GO_TO_BANK_GATEWAY_NAMESPACE": "azbankgateways:go-to-bank-gateway",
    # "SAMPLE_RESULT_NAMESPACE": "azbankgateways:sample-result",
}
```

Only the banks you actually create need entries; missing required keys raise `SettingDoesNotExist` at
`create()` time; a bank type missing from `GATEWAYS` raises `KeyError` (`readers/defaults.py:21`).

Custom readers (e.g. secrets from DB/env per tenant): subclass `azbankgateways.readers.bases.Reader` and
implement `read(bank_type, identifier) -> dict`, `default(identifier)`, `currency(identifier)`,
`get_bank_priorities(identifier)`; `klass()` is inherited (reads `BANK_CLASS`).

### URLs (`urls.py`)

```python
app_name = "azbankgateways"
_urlpatterns = [path("callback/", callback_view, name="callback")]
if not settings.IS_SAFE_GET_GATEWAY_PAYMENT:
    _urlpatterns += [path("go-to-bank-gateway/", go_to_bank_gateway, name="go-to-bank-gateway")]
if settings.IS_SAMPLE_FORM_ENABLE:
    _urlpatterns += [path("sample-payment/", ...), path("sample-result/", ...)]

def az_bank_gateways_urls():
    return _urlpatterns, app_name, app_name   # (patterns, app_name, namespace) tuple — pass straight to path()
```

```python
# project urls.py
from azbankgateways.urls import az_bank_gateways_urls
urlpatterns = [path("bankgateways/", az_bank_gateways_urls())]   # -> reverse("azbankgateways:callback")
```

If you nest it (e.g. under `api/` with namespace `api:payment`), set `CUSTOM_APP: "api:payment"` so `reverse()`
inside the library works.

---

## 3. Supported providers (2.3.4)

`models/enum.py` `BankType` + `default_settings.BANK_CLASS`:

| BankType | Class | Gateway currency | Sandbox | Callback data source | Pay redirect method |
|---|---|---|---|---|---|
| `BMI` (Sadad / Bank Melli) | `banks.BMI` | IRR | no | **POST** `Token` | GET `https://sadad.shaparak.ir/VPG/Purchase?Token=` |
| `SEP` (Saman) | `banks.SEP` | IRR | no | GET `ResNum`, `Token`, `RefNum`, `State` (`GetMethod=true`) | POST form |
| `ZARINPAL` | `banks.Zarinpal` (v4 API) | **IRT** | **yes** `SANDBOX:1` → `sandbox.zarinpal.com` | GET `Authority`, `Status` | GET `.../pg/StartPay/<authority>` |
| `ZIBAL` | `banks.Zibal` | IRR | no flag (use merchant `"zibal"`, Zibal's own test merchant) | GET `trackId` | GET `.../start/<trackId>` |
| `BAHAMTA` | `banks.Bahamta` | IRR | no | GET `reference` | GET (url from API) |
| `MELLAT` (Behpardakht) | `banks.Mellat` (SOAP/zeep) | IRR | no | **POST** `RefId`, `SaleReferenceId`... | GET `startpay.mellat?RefId=` |
| `IRANDARGAH` | `banks.irandargah.IranDargah` | IRR | **yes** `SANDBOX:1` → `https://dargaah.ir/sandbox/...` | **POST** `authority` | GET `.../ird/startpay/<authority>` |
| `ASANPARDAKHT` | `banks.asanpardakht.AsanPardakht` | IRR | no | GET `localInvoiceId` | POST form `RefId` |

IDPay and Pay.ir: **removed in 2.3.x** (no IDPay sandbox header exists any more). Note `IranDargah` and
`AsanPardakht` are not re-exported from `azbankgateways.banks` (import from their modules).

Sandbox code:

```python
# banks/zarinpal.py:19-28
kwargs.setdefault("SANDBOX", 0)
...
self._payment_type = 'payment'
if self._sandbox:
    self._payment_type = 'sandbox'
self._payment_url  = f"https://{self._payment_type}.zarinpal.com/pg/v4/payment/request.json"
self._startpay_url = f"https://{self._payment_type}.zarinpal.com/pg/StartPay/"
self._verify_url   = f"https://{self._payment_type}.zarinpal.com/pg/v4/payment/verify.json"

# banks/irandargah.py:23-31
self._sandbox = kwargs.get("SANDBOX", 0) == 1
base_url = "https://dargaah.ir" + ("/sandbox" if self._sandbox else "")
```

---

## 4. Model `azbankgateways.models.Bank` (`models/banks.py`)

```python
class Bank(models.Model):
    status = CharField(max_length=50, choices=PaymentStatus.choices)            # no default!
    bank_type = CharField(max_length=50, choices=BankType.choices)
    tracking_code = CharField(max_length=255)          # generated locally; NOT unique, NOT indexed
    amount = CharField(max_length=10)                  # STRING, in YOUR CURRENCY setting (pre-conversion)
    reference_number = CharField(unique=True, max_length=255)   # bank token/authority (SEP: replaced by RefNum)
    response_result = TextField(null=True, blank=True) # last bank message text at ready()
    callback_url = TextField()                         # your client callback URL
    extra_information = TextField(null=True, blank=True)   # bank-specific (JSON for Zibal/Bahamta/Mellat/Asan, k=v for BMI/SEP)
    bank_choose_identifier = CharField(max_length=255, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True); update_at = DateTimeField(auto_now=True)
    objects = BankManager()      # .update_expire_records(), .filter_return_from_bank()
    @property
    def is_success(self): return self.status == PaymentStatus.COMPLETE
```

* No FK to anything; no `Meta.ordering`, no index on `tracking_code`. Link from your own model.
* `amount` max 10 chars → max 9,999,999,999 in your currency.
* `extra_information` per bank on success: Zibal = full verify JSON (includes `amount`, `refNumber`, `cardNumber`);
  Bahamta = `result` JSON; BMI = `"RetrivalRefNo=...,SystemTraceNo={response_json['SystemTraceNo']}"` (bug: the
  second part is not an f-string); SEP = `TRACENO=..., RefNum=..., Token=...`; Mellat = full callback POST JSON;
  AsanPardakht = `{"payGateTranID": ...}`; Zarinpal/IranDargah = nothing (ref_id is **not** stored!).

### `PaymentStatus` (`models/enum.py`) — exact values

```python
class PaymentStatus(models.TextChoices):
    WAITING = "WAITING"
    REDIRECT_TO_BANK = "REDIRECT_TO_BANK"
    RETURN_FROM_BANK = "RETURN_FROM_BANK"
    CANCEL_BY_USER = "CANCEL_BY_USER"
    EXPIRE_GATEWAY_TOKEN = "EXPIRE_GATEWAY_TOKEN"
    EXPIRE_VERIFY_PAYMENT = "EXPIRE_VERIFY_PAYMENT"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"        # defined but never set by any code path
class CurrencyEnum(models.TextChoices):
    IRR = "IRR"; IRT = "IRT"
    rial_to_toman(amount) -> amount / 10     # true division -> float!
    toman_to_rial(amount) -> amount * 10
```

Note `CANCEL_BY_USER` is used for **every** negative verify result (user cancel, wrong amount, bank error).

### Migrations

`0001_initial` … `0006_alter_bank_bank_type` (0006 generated by Django 6.0.1 on 2026-01-07, aligns choices after
IDPay/PayV1 removal). On Django 5.2.19: `makemigrations --check` → **No changes detected**.

---

## 5. Initiation flow

### Factory (`bankfactories.py`)

```python
class BankFactory:
    def create(self, bank_type: BankType = None, identifier: str = "1") -> BaseBank:
        if not bank_type: bank_type = reader.default(identifier)
        bank_klass, bank_settings = self._import_bank(bank_type, identifier)
        bank = bank_klass(**bank_settings, identifier=identifier)
        bank.set_currency(reader.currency(identifier))          # CURRENCY setting
        return bank

    def auto_create(self, identifier="1", amount=None) -> BaseBank:
        for bank_type in reader.get_bank_priorities(identifier):
            try:
                bank = self.create(bank_type, identifier)
                bank.check_gateway(amount)     # !!! performs a REAL pay() request (token request) as a health check
                return bank
            except Exception as e: errors.append(e)
        raise BankGatewayAutoConnectionFailed(...)
```

`auto_create()` issues a throw-away token request on every bank tried (side effect at providers; with no
`request` set it falls back to `build_full_url()`, which needs `django.contrib.sites` for an absolute
callback URL). Prefer explicit `create(BankType.X)`.

`bankfactories_interface.BankFactory` is a convenience subclass:
`create(request, amount, callback_url, mobile_number=None, bank_type=None, identifier="1")` = create + the four setters.

### BaseBank (`banks/banks.py`)

```python
bank.set_request(request)               # used to build absolute callback URL (request.build_absolute_uri)
bank.set_amount(amount)                 # int(amount) > 0, stored in YOUR currency
bank.set_client_callback_url(url)       # where the library redirects the user after callback (+ ?tc=...)
bank.set_mobile_number("09...")         # optional
bank.set_custom_data({...})             # optional: merged into the provider pay-request body (data.update)
record = bank.ready()                   # -> Bank instance
```

`ready()` (`banks.py:124-138`):

```python
def ready(self) -> Bank:
    self.pay()                                    # prepare_amount(), generate tracking_code, HTTP token request
    bank = Bank.objects.create(
        bank_choose_identifier=self.identifier, bank_type=self.get_bank_type(),
        amount=self.get_amount(), reference_number=self.get_reference_number(),
        response_result=self.get_transaction_status_text(), tracking_code=self.get_tracking_code(),
    )                                             # status saved as "" first
    self._bank = bank
    self._set_payment_status(PaymentStatus.WAITING)     # save()
    if self._client_callback_url:
        self._bank.callback_url = self._client_callback_url   # set in memory ONLY, persisted by the next save
    return bank
```

**Verified at runtime:** after `ready()` the DB row has `status='WAITING', callback_url=''`. The callback URL is only
persisted when you call `get_gateway()` / `redirect_gateway()` on the **same instance** (they save via
`_set_payment_status(REDIRECT_TO_BANK)`). Always call one of them right after `ready()` in the same request.

Tracking code (`prepare_pay`, `banks.py:96`):
`int(str(uuid.uuid4().int)[-TRACKING_CODE_LENGTH:])` — random int; leading zeros are dropped (got 15 digits at
length 16 in testing). Not unique-constrained; collision odds are negligible but not zero.

Callback URL sent to the bank (`_get_gateway_callback_url`, `banks.py:382-394`):

```python
url = reverse(settings.CALLBACK_NAMESPACE)
if not absolute: url = self.get_request().build_absolute_uri(url)
query = dict(parse.parse_qsl(self.get_request().GET.urlencode()))   # COPIES the initiating request's GET params!
query.update({"bank_type": self.get_bank_type()}); query.update({"identifier": self.identifier})
url = append_querystring(url, query)
```

Observed: `http://shop.example/bankgateways/callback/?foo=bar&bank_type=ZARINPAL&identifier=1`. Behind a reverse
proxy set `SECURE_PROXY_SSL_HEADER` / `USE_X_FORWARDED_HOST` so the scheme/host are right; avoid initiating from a
URL with sensitive query params.

### Sending the user to the bank

```python
def get_gateway(self):                    # works in both modes; RECOMMENDED (API-friendly)
    self._verify_payment_expiry()         # raises BankGatewayTokenExpired if > 120 s since ready()
    self._set_payment_status(PaymentStatus.REDIRECT_TO_BANK)
    return {"params": params, "url": url, "method": method}

def redirect_gateway(self):               # raises SafeSettingsEnabled if IS_SAFE_GET_GATEWAY_PAYMENT
    self._verify_payment_expiry()
    self._set_payment_status(PaymentStatus.REDIRECT_TO_BANK)
    return redirect(self.get_gateway_payment_url())
    # -> /bankgateways/go-to-bank-gateway/?url=<bank>&method=GET|POST&<params>  (absolute if request set)
```

Observed Zarinpal sandbox: `{'params': {}, 'url': 'https://sandbox.zarinpal.com/pg/StartPay/A0000TEST', 'method': 'GET'}`.
For a DRF API, return this dict as JSON; the SPA does `location.href = url` for GET with empty params, or builds
and submits a `<form method=... action=url>` with hidden inputs (needed for SEP and AsanPardakht, which are POST).

`go_to_bank_gateway` view (`views/banks.py:30-39`, only when `IS_SAFE_GET_GATEWAY_PAYMENT=False`): reads `url`,
`method` and every other GET param from the query string and renders `azbankgateways/redirect_to_bank.html`,
an auto-submitting form **including `{% csrf_token %}`**. Because `url` is taken from the query string, anyone can
craft a link that auto-posts to an arbitrary site (open redirect plus CSRF token leak). This is why the README
recommends `IS_SAFE_GET_GATEWAY_PAYMENT: True`.

---

## 6. Callback flow — **the library verifies inside its own callback view**

`views/banks.py`:

```python
@csrf_exempt
def callback_view(request):                      # url name "azbankgateways:callback", GET or POST
    bank_type = request.GET.get("bank_type", None)
    identifier = request.GET.get("identifier", None)
    if not bank_type:
        raise Http404
    bank = BankFactory().create(bank_type, identifier=identifier)
    try:
        bank.verify_from_gateway(request)        # parses bank params, sets RETURN_FROM_BANK, calls verify()
    except AZBankGatewaysException:
        logging.exception("Verify from gateway failed.", stack_info=True)
    return bank.redirect_client_callback()       # 302 to <your callback_url>?tc=<tracking_code>
```

```python
# banks.py:144-162
def verify_from_gateway(self, request):
    self.set_request(request)
    self.prepare_verify_from_gateway()                     # bank-specific: read token, _set_bank_record()
    self._set_payment_status(PaymentStatus.RETURN_FROM_BANK)   # raises BankGatewayStateInvalid unless status == REDIRECT_TO_BANK
    self.verify(self.get_tracking_code())

def get_client_callback_url(self):
    return append_querystring(self._bank.callback_url, {settings.TRACKING_CODE_QUERY_PARAM: self.get_tracking_code()})
```

```python
# banks.py:113-122 + 200-219 — shared verify prelude
def prepare_verify(self, tracking_code):
    self._set_tracking_code(tracking_code)
    self._set_bank_record()     # Bank.objects.get((Q(reference_number=ref) | Q(tracking_code=tc)) & Q(bank_type=...))
    self.prepare_amount()       # amount reloaded from the DB row, converted to gateway currency
```

The provider-specific `verify()` calls the provider's verify API and sets **`COMPLETE`** on success, otherwise
**`CANCEL_BY_USER`**, e.g. Zarinpal (`banks/zarinpal.py:119-127`):

```python
def verify(self, transaction_code):
    super().verify(transaction_code)
    result = self._send_data(api=self._verify_url,
                             data={"merchant_id": ..., "authority": ref, "amount": self.get_gateway_amount()})
    if result['data'] and result['data']['code'] in [100, 101]:   # 101 = already verified
        self._set_payment_status(PaymentStatus.COMPLETE)
    else:
        self._set_payment_status(PaymentStatus.CANCEL_BY_USER)
```

**So who verifies?** The library does, synchronously, inside `azbankgateways:callback`, before redirecting the user
to your client callback URL with `?tc=<tracking_code>`. Your client callback view should **only read**
`Bank.objects.get(tracking_code=tc)` and check `status`/`is_success`. It must **not** call `bank.verify()` again
(see the idempotency notes below). Calling `BankFactory().create(bank_type=..., identifier=...).verify(tracking_code)`
yourself is only for re-verifying records left in `RETURN_FROM_BANK` (provider timeout during callback), as in the
README "re-verify" snippet:

```python
Bank.objects.update_expire_records()   # RETURN_FROM_BANK >15min -> EXPIRE_VERIFY_PAYMENT; REDIRECT_TO_BANK >15min -> EXPIRE_GATEWAY_TOKEN
for item in Bank.objects.filter_return_from_bank():
    bank = factory.create(bank_type=item.bank_type, identifier=item.bank_choose_identifier)
    bank.verify(item.tracking_code)
```

### Idempotency (tested on Django 5.2 with mocked Zarinpal)

* **Callback replay is safe at the status level:** the second hit raises `BankGatewayStateInvalid` (status already
  `COMPLETE` ≠ `REDIRECT_TO_BANK`), which is caught and logged, and the user is redirected again to the same
  `?tc=`. Status stays `COMPLETE`. Observed:
  `callback replay: 302 /pay/result/?order=42&tc=911648348450149 status='COMPLETE'`.
* **`bank.verify()` itself is NOT idempotent and has no status guard.** A manual `verify(tc)` on a `COMPLETE` record
  whose gateway replies negatively **downgrades it to `CANCEL_BY_USER`**. Observed:
  `manual verify() on COMPLETE record with failing gateway reply -> status='CANCEL_BY_USER'`.
  Many providers return an error on a second verify (BMI, SEP, Zibal "already verified" = 201, Mellat 43,
  Bahamta), so never re-verify `COMPLETE` rows. Your own order finalization must be idempotent independently.
* No `select_for_update`/locking: two concurrent callbacks can both pass the `REDIRECT_TO_BANK` check (race).
* **Unknown or forged token → HTTP 500:** if `_set_bank_record()` fails, `self._bank` stays `None` and
  `redirect_client_callback()` raises `AttributeError: 'NoneType' object has no attribute 'callback_url'`
  (observed). Same for a missing BMI token or a SEP `ResNum` not found. Expect 500s on bad callbacks
  (Sentry noise), not a redirect.
* `RETURN_FROM_BANK` is a real intermediate state: if the verify HTTP call raises `BankGatewayConnectionError`, the
  row stays `RETURN_FROM_BANK`, the user is still redirected to your callback, and you need the re-verify job above.
* Zarinpal: status `NOK` is not checked; verify is called anyway (gateway returns error → `CANCEL_BY_USER`).

### Amount validation

* `prepare_amount()` (`banks.py:57-69`) converts and enforces `gateway_amount >= get_minimum_amount()` (1000, in
  gateway currency for all banks) else `AmountDoesNotSupport`.
* At verify, the amount sent to the provider is the **DB `Bank.amount`** (converted), not something from the
  callback request. Providers that check amount server-side on verify: **Zarinpal, IranDargah, Bahamta** (amount
  in the verify body). **AsanPardakht** compares `TranResult.amount` with `int(bank.amount)` (`asanpardakht.py:259-273`,
  note: compares IRR from the gateway with the stored amount in *your* currency → breaks with `CURRENCY="IRT"`).
  **BMI, SEP, Zibal, Mellat: no amount comparison** in the library (SEP's verify response `TransactionDetail.AffectiveAmount`
  is ignored; Zibal's amount is only stored in `extra_information`).
* Therefore your app must check that `int(bank_record.amount) == expected_amount_in_CURRENCY` (guards against your
  own linking mistakes) and, for higher assurance, parse `extra_information` where available.

### Currency conversion — exact code (`banks.py:57-66`, `models/enum.py:20-26`)

```python
def prepare_amount(self):
    if self._currency == self._gateway_currency:
        self._gateway_amount = self._amount
    elif self._currency == CurrencyEnum.IRR and self._gateway_currency == CurrencyEnum.IRT:
        self._gateway_amount = CurrencyEnum.rial_to_toman(self._amount)    # amount / 10  -> float
    elif self._currency == CurrencyEnum.IRT and self._gateway_currency == CurrencyEnum.IRR:
        self._gateway_amount = CurrencyEnum.toman_to_rial(self._amount)    # amount * 10
    else:
        self._gateway_amount = self._amount
```

* `CURRENCY` = your app's unit. Gateway units: Zarinpal = IRT (and it sends `"currency": "IRT"`), all others IRR.
* **IRT → IRR multiplies by 10** (int stays int). **IRR → IRT divides by 10 with true division → float**. Observed
  with `CURRENCY="IRR"`, amount 150000: Zarinpal request `{'amount': 15000.0, 'currency': CurrencyEnum.IRT, ...}`.
  Amounts not divisible by 10 become e.g. `15000.5`. Recommendation: **`CURRENCY: "IRT"`** if you mainly use
  Zarinpal and price in toman (no division, integer), or `IRR` with amounts always multiples of 10.
* `Bank.amount` stores the **pre-conversion** amount (your currency) as a string.

---

## 7. Signals / hooks / admin / logging

* **No Django signals**, no callbacks/hooks. Extension points: subclass a bank class and point the top-level
  `CLASS` setting (or a custom Reader `klass()`) at it; `set_custom_data()` for extra pay-request fields;
  override `CALLBACK_NAMESPACE` to route the bank callback to your own view (then you must replicate
  `callback_view`).
* **Admin:** `admin.py` registers `Bank` automatically (`admin.site.register(Bank, BankAdmin)`), all fields
  read-only, filters on status/bank_type/dates. Registered on the default `admin.site` at import; unregister if
  unwanted. The admin "Bank result"/"Extra information" show raw provider data (BMI/SEP references, Mellat POST
  incl. `CardHolderPan` masked PAN, Zibal cardNumber).
* **Logging:** uses the **root logger** (`logging.debug/critical/exception`), no named logger (open issue #77). On
  timeout/connection errors it logs the full request body: `logging.exception("ZARINPAL time out gateway {}".format(data))`,
  which **includes `merchant_id`** (Zarinpal), `merchant` (Zibal), `api_key` (Bahamta, also in GET query string),
  `merchantID` (IranDargah), `merchantConfigurationId` (Asan), and BMI `SignData`. Mellat's `userPassword` and
  Asan's `usr/pwd` headers are not logged. Configure the root logger / filters so these don't reach shared log
  sinks at ERROR level, or add a logging filter.

---

## 8. Testing / fake bank

* There is **no fake/test bank** in the library (open issue #75 "تست بانک" asks for it). Options:
  1. **Mock HTTP** at the provider module: `mock.patch("azbankgateways.banks.zarinpal.requests.post", side_effect=fake)`
     (each bank imports `requests` in its own module; Mellat uses `zeep.Client` → patch `Mellat._get_client`).
     This drives the real code path end-to-end, as I did here (see §11).
  2. **Custom fake bank class** registered through the top-level `CLASS` setting, e.g.
     `CLASS = {**default_map, "ZARINPAL": "payments.testing.FakeZarinpal"}` in test settings; must be set before
     `azbankgateways.default_settings` is first imported. `BankType` is a closed TextChoices, so a fake must reuse
     an existing type key.
  3. Simplest for app-level tests: create `Bank` rows directly (`Bank.objects.create(status=COMPLETE, tracking_code=..., amount="150000", reference_number=uuid4().hex, bank_type="ZARINPAL", callback_url="/x")`)
     and hit your client-callback view with `?tc=`.
* Real sandboxes: Zarinpal `SANDBOX: 1` (`sandbox.zarinpal.com`, any UUID merchant), IranDargah `SANDBOX: 1`
  (`dargaah.ir/sandbox`), Zibal merchant `"zibal"`. Others have none.
* Settings caching: patch `azbankgateways.default_settings.X` (and `azbankgateways.banks.banks.settings` is the
  same module object, so patching the module attribute works).

---

## 9. Pitfalls & compatibility

1. **CSRF:** `callback_view` and `go_to_bank_gateway` are `@csrf_exempt` (POST callbacks from BMI/Mellat/IranDargah
   work; verified POST returns 302). If you override `CALLBACK_NAMESPACE` with your own view, add `@csrf_exempt`.
   The bank POST is cross-site, so **`SESSION_COOKIE_SAMESITE`/`CSRF_COOKIE_SAMESITE="Lax"` mean the user's session
   cookie is not sent on POST callbacks**. The library doesn't use sessions, but your client callback is reached by a
   302 from a cross-site POST, so session cookies may be missing on that hop (Lax cookies are sent on top-level GET
   navigations, which a 302 to GET normally is, but don't rely on `request.user` there; look up by `tc`).
2. **No session usage** in the library at all; state is purely in the `Bank` row + query params.
3. `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"` mandatory for BMI/SEP (Django's default is
   `"same-origin"` → BMI/SEP `create()` raises).
4. **120-second window** between `ready()` and `get_gateway()` (`(timezone.now() - created_at).seconds > 120`; uses
   `.seconds`, not `total_seconds()`). Call them in the same request.
5. `callback_url` is not persisted by `ready()` (see §5).
6. `IS_SAFE_GET_GATEWAY_PAYMENT=False` exposes an open-redirect + CSRF-token-leaking auto-submit page. Set `True`.
7. `update_expire_records()` uses naive `datetime.datetime.now()` → `RuntimeWarning: DateTimeField ... received a
   naive datetime while time zone support is active` under `USE_TZ=True` (observed on 5.2), and is wrong by the
   UTC offset if `TIME_ZONE` ≠ server local time. Nothing calls it automatically (no management command / celery).
8. Bad/forged callback → 500 (AttributeError), not 404.
9. `auto_create()` makes real token requests as a health check.
10. `reference_number` is `unique=True`; banks that fail before getting a token never create a row (pay() raises
    before `Bank.objects.create`), so no empty-string collisions in practice.
11. Initiating request's query string is copied into the bank callback URL.
12. Zarinpal: `ref_id` from verify response is not stored (only status), so you can't show the bank receipt
    number for Zarinpal unless you subclass `verify()`. Zarinpal also checks the callback domain strictly (issue #155).
13. `AutoField` (int32) PK for `Bank` regardless of `DEFAULT_AUTO_FIELD`.
14. Django 5.x: **no incompatibilities found** — `check` clean, `makemigrations --check` clean, `migrate` OK,
    full flow works on Django 5.2.19 / Python 3.12.3. `six` still required (Python 2 shim, harmless).

Open GitHub issues of note (14 open as of today): #31 verify handling when the provider is unavailable, #30 celery
beat periodic re-verify, #77 configurable logger, #75 test bank, #155 (PR) custom Zarinpal callback URL, #178 new
Mellat version, #122 Mellat payment ID, plus feature requests for new gateways (#159 IranKish, #125 Vandar, #106
Jibit PR, #37 Paystar, #33 Sepah).

---

## 10. Recommended minimal integration (Django 5 + DRF)

Settings: `CURRENCY="IRT"` if prices are in toman (else IRR with multiples of 10), `IS_SAFE_GET_GATEWAY_PAYMENT=True`,
`IS_SAMPLE_FORM_ENABLE=False`, `SECURE_REFERRER_POLICY="strict-origin-when-cross-origin"`, proxy headers configured.

```python
# payments/models.py
from django.db import models
from azbankgateways.models import PaymentStatus

class PaymentAttempt(models.Model):
    class State(models.TextChoices):
        PENDING = "PENDING"; SUCCEEDED = "SUCCEEDED"; FAILED = "FAILED"

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payment_attempts")
    amount = models.PositiveBigIntegerField()                    # in settings CURRENCY units
    bank_type = models.CharField(max_length=50)
    tracking_code = models.CharField(max_length=255, unique=True, db_index=True)   # = azbankgateways Bank.tracking_code
    bank_record = models.OneToOneField("azbankgateways.Bank", on_delete=models.PROTECT, null=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True)
```

```python
# payments/views.py
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from azbankgateways import bankfactories, default_settings as az_settings
from azbankgateways.exceptions import AZBankGatewaysException
from azbankgateways.models import Bank, BankType, PaymentStatus


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user, status=Order.Status.AWAITING_PAYMENT)
    amount = order.payable_amount                      # same unit as AZ CURRENCY
    bank = bankfactories.BankFactory().create(BankType.ZARINPAL)
    bank.set_request(request._request)                 # plain HttpRequest; its GET params are copied into the callback URL
    bank.set_amount(amount)
    bank.set_client_callback_url(reverse("payments:result"))
    bank.set_mobile_number(request.user.phone)         # optional
    try:
        record = bank.ready()
        gateway = bank.get_gateway()                   # {"url", "method", "params"}; also persists callback_url
    except AZBankGatewaysException:
        return Response({"detail": "gateway_unavailable"}, status=503)
    PaymentAttempt.objects.create(order=order, amount=amount, bank_type=record.bank_type,
                                  tracking_code=record.tracking_code, bank_record=record)
    return Response(gateway)                           # SPA: GET -> location.href; POST -> build & submit form


def payment_result(request):                           # reached via 302 from azbankgateways:callback
    tc = request.GET.get(az_settings.TRACKING_CODE_QUERY_PARAM)
    attempt = get_object_or_404(PaymentAttempt, tracking_code=tc)
    finalize_attempt(attempt.pk)
    attempt.refresh_from_db()
    return redirect(f"{FRONTEND_URL}/orders/{attempt.order_id}/payment?state={attempt.state}")


def finalize_attempt(attempt_pk):
    with transaction.atomic():
        attempt = PaymentAttempt.objects.select_for_update().select_related("order").get(pk=attempt_pk)
        if attempt.state != PaymentAttempt.State.PENDING:
            return                                     # idempotent: already finalized
        record = Bank.objects.get(pk=attempt.bank_record_id)   # library already verified in its callback
        if record.status in (PaymentStatus.WAITING, PaymentStatus.REDIRECT_TO_BANK, PaymentStatus.RETURN_FROM_BANK):
            return                                     # not final yet (RETURN_FROM_BANK -> re-verify job)
        ok = (
            record.status == PaymentStatus.COMPLETE
            and record.tracking_code == attempt.tracking_code
            and int(record.amount) == attempt.amount == attempt.order.payable_amount
        )
        attempt.state = PaymentAttempt.State.SUCCEEDED if ok else PaymentAttempt.State.FAILED
        attempt.finalized_at = timezone.now()
        attempt.save(update_fields=["state", "finalized_at"])
        if ok:
            attempt.order.mark_paid(attempt)           # must itself be idempotent (status guard)
        # if COMPLETE but amount mismatch -> alert ops; money was taken
```

Re-verify job (cron/celery, every few minutes): for `Bank` rows in `RETURN_FROM_BANK` younger than ~15 min, call
`BankFactory().create(bank_type=row.bank_type, identifier=row.bank_choose_identifier).verify(row.tracking_code)`
inside try/except, then `finalize_attempt()`. **Never call `verify()` on rows not in `RETURN_FROM_BANK`.** Replace
`update_expire_records()` with your own tz-aware query if you need expiry.

Do not link by `reference_number` (SEP overwrites it with `RefNum` at callback). Link by `tracking_code` / FK.

---

## 11. Compatibility test results (Django 5.2)

Environment: `/tmp/azgw-research/venv`, Python 3.12.3, `pip install "Django>=5.2,<5.3" az-iranian-bank-gateways==2.3.4`
→ Django 5.2.19, az-iranian-bank-gateways 2.3.4, zeep 4.3.3, pycryptodome 4.5.0, requests 2.34.2, six 1.17.0.

| Check | Result |
|---|---|
| `python -c 'import azbankgateways'` | OK (`v2.3.4`) |
| `django.setup()` with minimal settings (USE_TZ, `DEFAULT_AUTO_FIELD=BigAutoField`) | OK, no warnings |
| `manage.py check` | `System check identified no issues (0 silenced).` |
| `makemigrations --check --dry-run` | `No changes detected` (exit 0) |
| `migrate` (sqlite) | OK |
| End-to-end Zarinpal sandbox flow with mocked `requests.post` (`/tmp/azgw-research/proj/flow_test.py`) | ready → `WAITING` (callback_url still `''`); get_gateway → `REDIRECT_TO_BANK`, URL `https://sandbox.zarinpal.com/pg/StartPay/A0000TEST`; GET callback → 302 `/pay/result/?order=42&tc=911648348450149`, status `COMPLETE`; replay → 302, still `COMPLETE`; POST callback → 302 (csrf_exempt OK); manual `verify()` with negative reply → **`CANCEL_BY_USER`** (downgrade); unknown Authority → **500 AttributeError** |
| `Bank.objects.update_expire_records()` | works, emits naive-datetime `RuntimeWarning`s |

Observed IRR→IRT conversion: `amount 150000 (IRR)` → Zarinpal payload `amount: 15000.0` (float).

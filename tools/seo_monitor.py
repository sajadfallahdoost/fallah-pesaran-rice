"""Run bounded public storefront and read-only Search Console checks as JSON."""

import argparse
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
import json
import os
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree
from zoneinfo import ZoneInfo


ORIGIN = "https://www.fallah-rice.ir"
SITEMAP = f"{ORIGIN}/sitemap.xml"
PATHS = (
    "/",
    "/category/rice",
    "/guides/kharid-berenj-irani",
    "/guides/tashkhis-keyfiyat-berenj",
    "/guides/tafavot-anvae-berenj",
    "/about",
    "/contact",
)
USER_AGENT = "FallahRice-SEOMonitor/1.0"
TIMEOUT = 8
MAX_BODY = 2 * 1024 * 1024
LINK_LIMIT = 12
PRIVATE_PATH = re.compile(r"^/(?:_next|admin|api|account|cart|checkout|payments|bankgateways)(?:/|$)")
QUERY_CHARACTERS = str.maketrans({"ي": "ی", "ك": "ک", "‌": " "})
METRICS = ("clicks", "impressions", "ctr", "position")
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = build_opener(NoRedirect)


def fetch(url, *, token=None, payload=None, read_body=True):
    headers = {"User-Agent": USER_AGENT}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with OPENER.open(Request(url, headers=headers, data=data), timeout=TIMEOUT) as response:
            body = response.read(MAX_BODY + 1) if read_body else b""
            if len(body) > MAX_BODY:
                raise ValueError("response exceeds body limit")
            return response.status, response.headers, body.decode("utf-8", errors="replace")
    except HTTPError as error:
        with error:
            return error.code, error.headers, ""


def public_url(url):
    if any(ord(char) < 32 for char in url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if f"{parts.scheme}://{parts.netloc}" != ORIGIN or parts.query or PRIVATE_PATH.match(unquote(parts.path)):
        return None
    return ORIGIN + quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.directives = []
        self.links = []
        self.heading_count = 0
        self.inside_title = False
        self.has_title = False
        self.has_description = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        name = (attrs.get("name") or "").lower()
        content = (attrs.get("content") or "").strip()
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonicals.append(attrs.get("href") or "")
        elif tag == "meta" and name in {"robots", "googlebot"}:
            self.directives.append(content)
        elif tag == "meta" and name == "description":
            self.has_description |= bool(content)
        elif tag == "title":
            self.inside_title = True
        elif tag == "h1":
            self.heading_count += 1
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self.inside_title = False

    def handle_data(self, data):
        if self.inside_title and data.strip():
            self.has_title = True


def robots_rules(body):
    """Read Googlebot rules, falling back to the wildcard group when absent."""
    groups = {"googlebot": [], "*": []}
    agents = []
    started_rules = False
    for line in body.splitlines():
        name, _, value = line.split("#", 1)[0].partition(":")
        name, value = name.strip().lower(), value.strip()
        if name == "user-agent":
            if started_rules:
                agents = []
                started_rules = False
            agents.append(value.lower())
        elif name in {"allow", "disallow"}:
            started_rules = True
            for agent in groups.keys() & set(agents):
                groups[agent].append((value, name == "allow"))
    return groups["googlebot"] or groups["*"]


def allowed_by_robots(url, rules):
    matches = []
    for rule, allow in rules:
        if not rule:
            continue
        pattern = re.escape(rule.removesuffix("$")).replace(r"\*", ".*")
        if re.match(pattern + ("$" if rule.endswith("$") else ""), urlsplit(url).path):
            matches.append((len(rule.encode()), allow))
    return max(matches, default=(0, True))[1]


def storefront():
    requests = {}
    issues = []

    def probe(url, read_body=True):
        if url not in requests:
            try:
                requests[url] = fetch(url, read_body=read_body)
            except (OSError, ValueError, URLError) as error:
                requests[url] = (None, {}, "")
                issues.append({"url": url, "issue": f"request failed ({type(error).__name__})"})
        return requests[url]

    redirects = {}
    for url in ("http://fallah-rice.ir/", "http://www.fallah-rice.ir/", "https://fallah-rice.ir/"):
        status, headers, _ = probe(url, read_body=False)
        location = headers.get("Location", "")
        redirects[url] = {"status": status, "location": location}
        if status not in {301, 308} or urljoin(url, location) != ORIGIN + "/":
            issues.append({"url": url, "issue": "expected a permanent redirect to the HTTPS canonical host"})

    robots_url = f"{ORIGIN}/robots.txt"
    robots_status, _, robots = probe(robots_url)
    if robots_status != 200 or not re.search(rf"^sitemap:\s*{re.escape(SITEMAP)}\s*$", robots, re.I | re.M):
        issues.append({"url": robots_url, "issue": "canonical Sitemap directive unavailable"})
    rules = robots_rules(robots)

    sitemap_status, _, sitemap = probe(SITEMAP)
    sitemap_urls = set()
    if sitemap_status == 200:
        try:
            root = ElementTree.fromstring(sitemap)
            if root.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
                raise ValueError("expected sitemap urlset")
            sitemap_urls = {node.text.strip() for node in root.findall("./{*}url/{*}loc") if node.text}
        except (ElementTree.ParseError, ValueError):
            issues.append({"url": SITEMAP, "issue": "invalid sitemap URL set"})
    else:
        issues.append({"url": SITEMAP, "issue": f"unexpected HTTP status {sitemap_status}"})
    if sitemap_urls:
        invalid = sorted(url for url in sitemap_urls if not public_url(url) or not allowed_by_robots(url, rules))
        if invalid:
            issues.append({"url": SITEMAP, "issue": "non-public or blocked URLs", "examples": invalid[:5]})

    candidates = {public_url(url) for url in sitemap_urls}
    tracking_url = f"{ORIGIN}/track"
    if tracking_url in candidates:
        issues.append({"url": tracking_url, "issue": "order tracking is listed in the sitemap"})
    products = sorted(url for url in candidates if url and url.startswith(f"{ORIGIN}/product/"))
    policies = sorted(url for url in candidates if url and url.startswith(f"{ORIGIN}/info/"))
    targets = [f"{ORIGIN}{path}" for path in PATHS] + products[:2] + policies[:2]
    pages = {}
    links = {}
    for url in targets:
        status, headers, body = probe(url)
        allowed = allowed_by_robots(url, rules) if robots_status == 200 else None
        page_report = {"status": status, "in_sitemap": url in candidates, "googlebot_allowed": allowed}
        pages[url] = page_report
        if status != 200:
            issues.append({"url": url, "issue": f"unexpected HTTP status {status}"})
            continue
        page = PageMetadata()
        page.feed(body)
        canonical = [public_url(href) for href in page.canonicals]
        directives = page.directives + headers.get_all("X-Robots-Tag", [])
        noindex = any(re.search(r"\b(?:noindex|none)\b", directive, re.I) for directive in directives)
        snippet_blocked = any(re.search(r"\b(?:nosnippet|max-snippet:\s*0\b)", directive, re.I) for directive in directives)
        page_report.update(canonical=page.canonicals, noindex=noindex, snippet_blocked=snippet_blocked,
                           robots_directives=directives, h1=page.heading_count)
        problems = []
        if canonical != [url]:
            problems.append("missing or mismatched canonical")
        draft_about = url == f"{ORIGIN}/about" and noindex and url not in candidates
        if allowed is False or (noindex and not draft_about):
            problems.append("indexing blocked")
        if snippet_blocked:
            problems.append("search previews restricted")
        if url not in candidates and not draft_about:
            problems.append("missing in sitemap")
        if not page.has_title or not page.has_description or not page.heading_count:
            problems.append("missing title, description, or h1")
        issues.extend({"url": url, "issue": problem} for problem in problems)
        for href in page.links:
            try:
                link = public_url(urljoin(url, href))
            except ValueError:
                continue
            if link and link not in targets:
                links.setdefault(link, url)

    checked_links = {}
    for url in list(links)[:LINK_LIMIT]:
        status, _, _ = probe(url, read_body=False)
        checked_links[url] = status
        if status is None or status >= 400:
            issues.append({"url": url, "issue": f"internal link returned {status}", "source": links[url]})

    return {
        "redirects": redirects,
        "robots_status": robots_status,
        "sitemap_status": sitemap_status,
        "sitemap_urls": len(sitemap_urls),
        "sitemap_products": len(products),
        "pages": pages,
        "internal_links": checked_links,
        "issues": issues,
        "request_count": len(requests),
    }


def search_console(use_adc):
    token = os.getenv("SEARCH_CONSOLE_ACCESS_TOKEN")
    if not token and use_adc:
        try:
            from google.auth import default
            from google.auth.transport.requests import Request as AuthRequest

            credentials, _ = default(scopes=[SCOPE])
            transport = AuthRequest()

            def refresh_request(*args, **kwargs):
                kwargs["timeout"] = TIMEOUT
                return transport(*args, **kwargs)

            credentials.refresh(refresh_request)
            token = credentials.token
        except ImportError:
            return {"status": "adc_dependencies_missing", "required": ["google-auth", "requests"]}
        except Exception as error:
            return {"status": "authentication_error", "error": type(error).__name__}
    if not token:
        return {"status": "credentials_unavailable"}

    property_url = os.getenv("SEARCH_CONSOLE_SITE_URL", "sc-domain:fallah-rice.ir")
    if property_url not in {"sc-domain:fallah-rice.ir", f"{ORIGIN}/"}:
        return {"status": "invalid_property"}
    analytics_url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(property_url, safe='')}/searchAnalytics/query"
    inspection_url = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"

    def query(endpoint, payload):
        try:
            status, _, body = fetch(endpoint, token=token, payload=payload)
            return json.loads(body) if status == 200 else {"http_status": status}
        except (OSError, ValueError, URLError) as error:
            return {"error": type(error).__name__}

    yesterday = datetime.now(ZoneInfo("America/Los_Angeles")).date() - timedelta(days=1)
    recent = query(analytics_url, {
        "startDate": (yesterday - timedelta(days=27)).isoformat(),
        "endDate": yesterday.isoformat(),
        "dimensions": ["date"],
        "type": "web",
        "dataState": "final",
    })
    completed_dates = [date.fromisoformat(row["keys"][0]) for row in recent.get("rows", [])]
    result = {"property": property_url, "status": "available" if completed_dates else "no_recent_finalized_rows"}
    if "error" in recent or "http_status" in recent:
        return {"property": property_url, "status": "analytics_unavailable", **recent}

    if completed_dates:
        latest = max(completed_dates)
        result["latest_finalized_date_with_data"] = latest.isoformat()
        result["periods"] = []
        page_filter = {"dimension": "page", "operator": "includingRegex", "expression":
                       r"^https://www\.fallah-rice\.ir(?:/?$|/(?:category|guides|product)(?:/|$)|/(?:shop|about|contact)$)"}
        query_filter = {"dimension": "query", "operator": "includingRegex", "expression":
                        r"فلاح|برنج|چ[اآ][یي]|روغن[\s‌]+ز[یي]تون"}
        for end in (latest, latest - timedelta(days=28)):
            window = {"startDate": (end - timedelta(days=27)).isoformat(), "endDate": end.isoformat(),
                      "type": "web", "dataState": "final"}
            period = {"start_date": window["startDate"], "end_date": window["endDate"]}
            for name, dimensions, filters in (
                ("property_total", [], []),
                ("target_pages", ["page"], [page_filter]),
                ("target_query_and_page", ["query", "page"], [query_filter, page_filter]),
            ):
                request = {**window, "dimensions": dimensions, "rowLimit": 100}
                if filters:
                    request["dimensionFilterGroups"] = [{"groupType": "and", "filters": filters}]
                response = query(analytics_url, request)
                if "error" in response or "http_status" in response:
                    period[name] = response
                    continue
                rows = []
                for row in response.get("rows", []):
                    keys = row.get("keys", [])
                    entry = {"keys": keys, **{metric: row.get(metric) for metric in METRICS}}
                    if name == "target_query_and_page" and keys:
                        entry["normalized_query"] = " ".join(keys[0].translate(QUERY_CHARACTERS).split())
                    rows.append(entry)
                period[name] = rows
            result["periods"].append(period)

    inspections = {}
    for path in PATHS[:3]:
        url = f"{ORIGIN}{path}"
        response = query(inspection_url, {"inspectionUrl": url, "siteUrl": property_url})
        inspections[url] = response.get("inspectionResult", {}).get("indexStatusResult", response)
    result["index_inspection"] = inspections
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-console-adc", action="store_true", help="Use authorized Google ADC with read-only scope after checking the token environment variable")
    args = parser.parse_args()
    if os.getenv("SEARCH_CONSOLE_USE_ADC") == "1":
        args.search_console_adc = True
    git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
    report = {
        "checked_at": datetime.now(ZoneInfo("Asia/Tehran")).isoformat(timespec="seconds"),
        "checkout_sha": git.stdout.strip() if git.returncode == 0 else None,
        "storefront": storefront(),
        "search_console": search_console(args.search_console_adc),
        "generative_ai": {"source": "Search Console Generative AI performance report", "status": "requires_official_ui_or_export"},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report["storefront"]["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())

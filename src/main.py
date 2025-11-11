thonimport argparse
import datetime as dt
import json
import logging
import os
import sys
from typing import Any, Dict, List, Set, Tuple

# Ensure submodule directories are importable when running as a script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

for subdir in ("extractors", "crawlers", "exporters"):
    path = os.path.join(BASE_DIR, subdir)
    if path not in sys.path:
        sys.path.append(path)

from email_detector import extract_emails  # type: ignore
from phone_parser import extract_phone_numbers  # type: ignore
from social_link_finder import extract_social_links  # type: ignore
from utils_cleaner import (  # type: ignore
    deduplicate_preserve_order,
    html_to_text,
    normalize_email,
    normalize_phone,
    normalize_url,
)

from static_crawler import StaticCrawler  # type: ignore
from dynamic_crawler import DynamicCrawler  # type: ignore
from json_exporter import export_to_json  # type: ignore  # noqa: E402

logger = logging.getLogger("deep_contact_scraper")

def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(REPO_ROOT, path)

def load_config(config_path: str | None) -> Dict[str, Any]:
    default_config: Dict[str, Any] = {
        "user_agent": "DeepContactScraper/1.0 (+https://bitbash.dev)",
        "timeout": 15,
        "max_depth": 2,
        "max_pages_per_site": 15,
        "use_dynamic_crawler": False,
        "dynamic_render_timeout": 15,
        "concurrent_requests": 4,
        "proxy": None,
        "regions_for_phones": ["DE", "AT", "CH", "SE", "NO", "DK", "FI", "IS"],
    }

    if not config_path:
        logger.info("No config path provided, using built-in defaults.")
        return default_config

    cfg_path = resolve_path(config_path)
    if not os.path.exists(cfg_path):
        logger.warning(
            "Config file %s not found. Falling back to default configuration.",
            cfg_path,
        )
        return default_config

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        default_config.update(loaded)
        logger.info("Loaded configuration from %s", cfg_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read config file %s: %s", cfg_path, exc)
    return default_config

def read_input_urls(input_path: str) -> List[str]:
    path = resolve_path(input_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")

    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            urls.append(normalize_url(raw))

    urls = deduplicate_preserve_order(urls)
    logger.info("Loaded %d unique root URL(s) from %s", len(urls), path)
    return urls

def choose_crawler(config: Dict[str, Any]) -> Any:
    headers = {"User-Agent": config.get("user_agent")}
    timeout = int(config.get("timeout", 15))
    max_depth = int(config.get("max_depth", 2))
    max_pages = int(config.get("max_pages_per_site", 15))
    proxy = config.get("proxy")

    if config.get("use_dynamic_crawler"):
        logger.info("Using dynamic crawler (JavaScript-capable).")
        return DynamicCrawler(
            headers=headers,
            timeout=timeout,
            max_depth=max_depth,
            max_pages_per_site=max_pages,
            proxy=proxy,
            render_timeout=int(config.get("dynamic_render_timeout", 15)),
        )

    logger.info("Using static crawler (fast HTML-only).")
    return StaticCrawler(
        headers=headers,
        timeout=timeout,
        max_depth=max_depth,
        max_pages_per_site=max_pages,
        proxy=proxy,
    )

def aggregate_contacts_for_site(
    root_url: str,
    pages: List[Dict[str, Any]],
    regions_for_phones: List[str],
) -> List[Dict[str, Any]]:
    """
    Aggregate extracted contact info into one or more records for the given root_url.
    """
    email_sources: Dict[str, str] = {}
    phone_sources: Dict[str, str] = {}
    social_sources: Dict[str, Tuple[str, str]] = {}  # link -> (platform, page)

    for page in pages:
        page_url = page.get("url", root_url)
        html = page.get("html", "")
        if not html:
            continue

        text = html_to_text(html)
        emails = {normalize_email(e) for e in extract_emails(html)}
        phones = {
            normalize_phone(p)
            for p in extract_phone_numbers(text, regions_for_phones)
        }

        social_links = extract_social_links(html)
        for email in emails:
            if email and email not in email_sources:
                email_sources[email] = page_url
        for phone in phones:
            if phone and phone not in phone_sources:
                phone_sources[phone] = page_url
        for entry in social_links:
            link = normalize_url(entry["url"])
            platform = entry["platform"]
            if link not in social_sources:
                social_sources[link] = (platform, page_url)

    logger.debug(
        "Aggregated for %s: %d emails, %d phones, %d social links",
        root_url,
        len(email_sources),
        len(phone_sources),
        len(social_sources),
    )

    if not (email_sources or phone_sources or social_sources):
        return []

    timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    records: List[Dict[str, Any]] = []

    # Primary record combining first email, first phone, all socials
    primary_email = next(iter(email_sources), None)
    primary_phone = next(iter(phone_sources), None)
    social_links_list = list(social_sources.keys())
    platforms = {platform for platform, _ in social_sources.values()}
    primary_platform = next(iter(platforms), None)

    primary_source_page = (
        email_sources.get(primary_email)
        or phone_sources.get(primary_phone)
        or (social_sources[social_links_list[0]][1] if social_links_list else root_url)
        or root_url
    )

    records.append(
        {
            "url": root_url,
            "email": primary_email,
            "phone": primary_phone,
            "socialLinks": social_links_list,
            "platform": primary_platform or ("Multiple" if platforms else None),
            "sourcePage": primary_source_page,
            "timestamp": timestamp,
        }
    )

    # Additional records for remaining emails and phones (one record per value)
    for email, src in email_sources.items():
        if email == primary_email:
            continue
        records.append(
            {
                "url": root_url,
                "email": email,
                "phone": None,
                "socialLinks": [],
                "platform": None,
                "sourcePage": src,
                "timestamp": timestamp,
            }
        )

    for phone, src in phone_sources.items():
        if phone == primary_phone:
            continue
        records.append(
            {
                "url": root_url,
                "email": None,
                "phone": phone,
                "socialLinks": [],
                "platform": None,
                "sourcePage": src,
                "timestamp": timestamp,
            }
        )

    # Additional records for socials if there were none in primary
    if not social_links_list:
        for link, (platform, src) in social_sources.items():
            records.append(
                {
                    "url": root_url,
                    "email": None,
                    "phone": None,
                    "socialLinks": [link],
                    "platform": platform,
                    "sourcePage": src,
                    "timestamp": timestamp,
                }
            )

    return records

def process_urls(
    urls: List[str],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    crawler = choose_crawler(config)
    all_records: List[Dict[str, Any]] = []
    regions = config.get("regions_for_phones") or []

    for idx, root_url in enumerate(urls, start=1):
        logger.info("(%d/%d) Crawling %s", idx, len(urls), root_url)
        try:
            pages = crawler.crawl(root_url)
            logger.info("Fetched %d page(s) for %s", len(pages), root_url)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to crawl %s: %s", root_url, exc)
            continue

        site_records = aggregate_contacts_for_site(root_url, pages, regions)
        if not site_records:
            logger.info("No contact data found for %s", root_url)
        else:
            logger.info(
                "Extracted %d contact record(s) from %s",
                len(site_records),
                root_url,
            )
        all_records.extend(site_records)

    return all_records

def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deep Email, Phone, & Social Media Scraper Search",
    )
    parser.add_argument(
        "--input",
        "-i",
        default="data/sample_input.txt",
        help="Path to input file containing a list of URLs (one per line).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/output.json",
        help="Path where the JSON results will be written.",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="src/config/settings.example.json",
        help="Path to configuration JSON file. If missing, defaults are used.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--use-dynamic",
        action="store_true",
        help="Force use of dynamic crawler (overrides config).",
    )
    parser.add_argument(
        "--use-static",
        action="store_true",
        help="Force use of static crawler (overrides config).",
    )
    return parser.parse_args(argv)

def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(args.verbose)

    config = load_config(args.config)

    if args.use_dynamic and args.use_static:
        logger.warning(
            "Both --use-dynamic and --use-static flags set. Defaulting to dynamic.",
        )
        config["use_dynamic_crawler"] = True
    elif args.use_dynamic:
        config["use_dynamic_crawler"] = True
    elif args.use_static:
        config["use_dynamic_crawler"] = False

    try:
        urls = read_input_urls(args.input)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read input URLs: %s", exc)
        sys.exit(1)

    if not urls:
        logger.error("No URLs provided in the input file. Nothing to do.")
        sys.exit(1)

    records = process_urls(urls, config)

    output_path = resolve_path(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    export_to_json(records, output_path)
    logger.info("Finished. Wrote %d record(s) to %s", len(records), output_path)

if __name__ == "__main__":
    main()
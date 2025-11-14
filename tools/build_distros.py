#!/usr/bin/env python3
"""
Utility script for bestlinuxdistros.com

Generates:
  • distros/<id>.html detail pages rendered from api/linux_distros_full.json
  • js/distro-data.js snapshot for offline/fallback usage
  • sitemap.xml entries for every public page

This keeps the JSON file as the single source of truth while producing
fully rendered static pages for SEO and offline use.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
import base64
from io import BytesIO
from urllib.parse import quote_plus, urlencode, urlparse
from urllib.request import Request, urlopen

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    Image = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_PATH = PROJECT_ROOT / "api" / "linux_distros_full.json"
DISTRO_DIR = PROJECT_ROOT / "distros"
SNAPSHOT_PATH = PROJECT_ROOT / "js" / "distro-data.js"
SITEMAP_PATH = PROJECT_ROOT / "sitemap.xml"
BASE_URL = "https://bestlinuxdistros.com"
ASSET_ROOT = PROJECT_ROOT / "assets"
OG_DIR = ASSET_ROOT / "og"
LOGO_DIR = ASSET_ROOT / "logos"
UA_HEADER = {"User-Agent": "bestlinuxdistros-bot/1.0"}
CLEARBIT_BASE = "https://logo.clearbit.com/"
BLANK_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4AWNgYGD4DwABBAEAAlSCDQAAAABJRU5ErkJggg=="
)
LOGO_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}

# Manual metadata that is not bundled with the upstream feed.
# release_model -> {"LTS","Rolling","Release","Hybrid"}
# popularity_rank -> smaller number == more popular
METADATA = {
    "ubuntu": {"release_model": "LTS", "popularity_rank": 1},
    "debian": {"release_model": "LTS", "popularity_rank": 2},
    "fedora": {"release_model": "Release", "popularity_rank": 3},
    "arch": {"release_model": "Rolling", "popularity_rank": 4},
    "manjaro": {"release_model": "Rolling", "popularity_rank": 5},
    "mint": {"release_model": "LTS", "popularity_rank": 6},
    "popos": {"release_model": "LTS", "popularity_rank": 7},
    "zorin": {"release_model": "LTS", "popularity_rank": 8},
    "kali": {"release_model": "Rolling", "popularity_rank": 9},
    "rhel": {"release_model": "LTS", "popularity_rank": 10},
    "elementary": {"release_model": "LTS", "popularity_rank": 11},
    "mxlinux": {"release_model": "LTS", "popularity_rank": 12},
    "opensuse": {"release_model": "Hybrid", "popularity_rank": 13},
    "gentoo": {"release_model": "Rolling", "popularity_rank": 14},
    "slackware": {"release_model": "Release", "popularity_rank": 15},
    "alpine": {"release_model": "Rolling", "popularity_rank": 16},
    "tails": {"release_model": "Rolling", "popularity_rank": 17},
    "parrot": {"release_model": "Rolling", "popularity_rank": 18},
    "nixos": {"release_model": "Rolling", "popularity_rank": 19},
    "clearlinux": {"release_model": "Rolling", "popularity_rank": 20},
    "centos": {"release_model": "LTS", "popularity_rank": 21},
    "almalinux": {"release_model": "LTS", "popularity_rank": 22},
    "rocky": {"release_model": "LTS", "popularity_rank": 23},
    "endeavouros": {"release_model": "Rolling", "popularity_rank": 24},
    "garuda": {"release_model": "Rolling", "popularity_rank": 25},
    "void": {"release_model": "Rolling", "popularity_rank": 26},
    "solus": {"release_model": "Rolling", "popularity_rank": 27},
    "deepin": {"release_model": "Release", "popularity_rank": 28},
    "peppermint": {"release_model": "LTS", "popularity_rank": 29},
    "qubes": {"release_model": "Release", "popularity_rank": 30},
}

BEGINNER_HINTS = {
    "ubuntu",
    "mint",
    "popos",
    "zorin",
    "elementary",
    "mxlinux",
    "peppermint",
    "deepin",
    "solus",
}
SERVER_HINTS = {"debian", "rhel", "centos", "almalinux", "rocky", "clearlinux"}
SECURITY_HINTS = {"kali", "tails", "parrot", "qubes"}

WIKI_TITLES = {
    "ubuntu": "Ubuntu",
    "debian": "Debian",
    "fedora": "Fedora Linux",
    "arch": "Arch Linux",
    "manjaro": "Manjaro (operating system)",
    "mint": "Linux Mint",
    "popos": "Pop!_OS",
    "zorin": "Zorin OS",
    "elementary": "Elementary OS",
    "mxlinux": "MX Linux",
    "opensuse": "OpenSUSE",
    "gentoo": "Gentoo Linux",
    "slackware": "Slackware",
    "alpine": "Alpine Linux",
    "tails": "Tails (operating system)",
    "parrot": "Parrot Security OS",
    "nixos": "NixOS",
    "clearlinux": "Clear Linux",
    "centos": "CentOS",
    "almalinux": "AlmaLinux",
    "rocky": "Rocky Linux",
    "kali": "Kali Linux",
    "rhel": "Red Hat Enterprise Linux",
    "endeavouros": "EndeavourOS",
    "garuda": "Garuda Linux",
    "void": "Void Linux",
    "solus": "Solus (operating system)",
    "deepin": "Deepin (operating system)",
    "peppermint": "Peppermint OS",
    "qubes": "Qubes OS",
}


def main() -> None:
    distros = json.loads(API_PATH.read_text(encoding="utf-8-sig"))
    ids = {item["id"] for item in distros}
    missing = ids.difference(METADATA)
    if missing:
        raise SystemExit(f"Metadata missing for ids: {sorted(missing)}")

    now = datetime.now(timezone.utc)
    last_updated_display = now.strftime("%B %d, %Y")
    generated_at_iso = now.isoformat()

    enriched = []
    for entry in distros:
        entry["website"] = normalize_url(entry.get("website", ""))
        entry["download_url"] = normalize_url(entry.get("download_url", ""))
        original_logo = (entry.get("logo") or "").strip()
        entry["logo_source"] = original_logo
        cached_logo = ensure_local_logo(entry["id"], original_logo, entry["website"], entry.get("name"))
        if cached_logo:
            entry["logo"] = cached_logo
            entry["logo_local"] = cached_logo
        else:
            entry["logo"] = original_logo
            entry["logo_local"] = ""
        wiki_title = WIKI_TITLES.get(entry["id"])
        if wiki_title:
            print(f"[BLD] Fetching screenshots for: {entry['id']}")
            print(f"[BLD] Wikipedia title: {wiki_title}")
            fetched = fetch_wiki_screenshots(wiki_title)
            print(f"[BLD] Found {len(fetched)} screenshot(s)")
            if fetched:
                entry["screenshots"] = fetched
        meta = METADATA[entry["id"]]
        enriched_entry = {**entry, **meta}
        enriched.append(enriched_entry)

    for enriched_entry in enriched:
        generate_og_image(enriched_entry, enriched_entry.get("screenshots") or [])
        html_page = render_detail_page(enriched_entry, last_updated_display, enriched)
        (DISTRO_DIR / f"{enriched_entry['id']}.html").write_text(html_page, encoding="utf-8")

    write_snapshot(enriched, generated_at_iso, last_updated_display)
    write_sitemap(enriched, now.date().isoformat())


def render_detail_page(distro: dict, last_updated: str, all_distros: list[dict]) -> str:
    """Render the HTML for a single distro detail page."""
    name = distro["name"]
    raw_desc = distro.get("description", "") or ""
    escaped_desc = safe_text(raw_desc)
    release_model = distro.get("release_model", "LTS")
    status = safe_text(distro.get("status", "Active"))
    meta_description_text = distro.get("seo_description") or (
        f"{name} Linux review covering a {release_model} cadence, hardware requirements, package tooling, and recommended use cases."
    )
    meta_description = safe_text(meta_description_text)
    lede_copy = escaped_desc or meta_description
    badges = build_badges(distro, release_model)
    badge_markup = "".join(
        f'<span class="pill" data-pill="{html.escape(badge)}">{html.escape(badge)}</span>'
        for badge in badges
    )
    category_badges = split_badges(distro.get("category", ""))
    category_markup = "".join(
        f'<span class="eyebrow-chip">{html.escape(label)}</span>' for label in category_badges
    )
    best_for = distro.get("compatibility", {}).get("best_for") or []
    not_ideal = distro.get("compatibility", {}).get("not_ideal_for") or []
    use_cases = distro.get("compatibility", {}).get("use_cases") or []
    target_users = distro.get("target_users") or []
    family = distro.get("family") or ""
    distro_badges = distro.get("badges") or []
    keyword_terms = distro_badges
    badge_chip_markup = "".join(
        f'<span class="tag-pill">{safe_text(label)}</span>' for label in distro_badges
    )
    download_url = distro.get("download_url") or ""
    official_site = distro.get("website") or ""

    hero_meta = [
        ("Origin", distro.get("origin") or "Global"),
        ("First release", distro.get("first_release") or "Unknown"),
        (
            "Architectures",
            ", ".join(distro.get("architecture") or []),
        ),
        ("Desktop", distro.get("desktop") or "Multiple"),
        ("Package manager", distro.get("package_manager") or "Unknown"),
    ]
    hero_meta_markup = "".join(
        f"""
        <article>
          <p class="muted-label">{safe_text(label)}</p>
          <p class="data-value">{safe_text(value)}</p>
        </article>
        """
        for label, value in hero_meta
        if value
    )
    hero_buttons: list[str] = []
    if download_url:
        hero_buttons.append(
            f'<a class="primary-btn" href="{html.escape(download_url)}" target="_blank" rel="noopener">Download {safe_text(name)}</a>'
        )
    if official_site:
        hero_buttons.append(
            f'<a class="ghost-btn" href="{html.escape(official_site)}" target="_blank" rel="noopener">Official Website</a>'
        )
    hero_buttons.append(
        f'<a class="ghost-btn" href="../compare.html?ids={distro["id"]}">Add to compare</a>'
    )
    hero_actions_markup = "\n                    ".join(hero_buttons)

    info_cards = [
        ("Origin", distro.get("origin") or "Global"),
        ("Architectures", ", ".join(distro.get("architecture") or [])),
        ("Desktop environment", distro.get("desktop") or "Multiple"),
        ("Package manager", distro.get("package_manager") or "Unknown"),
        ("Release model", release_model),
        ("Status", distro.get("status") or "Active"),
    ]
    info_markup = "".join(
        f"""
        <article>
          <p class="muted-label">{safe_text(label)}</p>
          <p class="data-value">{safe_text(value)}</p>
        </article>
        """
        for label, value in info_cards
        if value
    )

    pros_markup = "".join(f"<li>{safe_text(item)}</li>" for item in distro.get("pros", []))
    cons_markup = "".join(f"<li>{safe_text(item)}</li>" for item in distro.get("cons", []))

    hw_min = distro.get("hardware_requirements", {}).get("minimum") or {}
    hw_rec = distro.get("hardware_requirements", {}).get("recommended") or {}
    hw_rows = [
        ("CPU", hw_min.get("cpu"), hw_rec.get("cpu")),
        ("RAM", hw_min.get("ram"), hw_rec.get("ram")),
        ("Storage", hw_min.get("storage"), hw_rec.get("storage")),
    ]
    hw_markup = "".join(
        f"<tr><td>{safe_text(spec)}</td><td>{safe_text(low or 'Not listed')}</td><td>{safe_text(high or 'Not listed')}</td></tr>"
        for spec, low, high in hw_rows
    )

    package_description = distro.get("package_manager_explained") or ""
    if not package_description:
        pm_name = distro.get("package_manager") or "its default package manager"
        package_description = (
            f"{name} uses {pm_name} to handle repositories, updates, and upgrades for this {release_model} cadence."
        )
    package_blurb = safe_text(package_description)
    package_name = safe_text(distro.get("package_manager") or "Not provided")
    screenshots = distro.get("screenshots") or []
    screenshot_sources = screenshots or build_placeholder_screenshots(name)
    screenshot_markup = "".join(
        f"""
        <div class="screenshot-card" data-full="{html.escape(url)}">
          <img src="{html.escape(url)}" alt="{safe_text(name)} screenshot" loading="lazy" decoding="async" />
        </div>
        """
        for url in screenshot_sources
    )

    benchmarks = distro.get("benchmarks") or {}
    boot_time = benchmarks.get("boot_time") or "Not published"
    resource_usage = benchmarks.get("resource_usage") or "Not published"
    stability = int(benchmarks.get("stability_score", 0) or 0)
    beginner = int(benchmarks.get("beginner_score", 0) or 0)
    power = int(benchmarks.get("power_user_score", 0) or 0)
    score_rows = [
        ("Stability", stability),
        ("Beginner friendly", beginner),
        ("Power user score", power),
    ]
    score_markup = "".join(
        (
            f"""
        <div class="score-row">
          <span>{html.escape(label)}</span>
          <div class="score-bar"><span style="width: {min(score,10)*10}%"></span></div>
          <strong>{score}/10</strong>
        </div>
        """
            if score
            else f"""
        <div class="score-row pending">
          <span>{html.escape(label)}</span>
          <p class="muted">Not rated yet</p>
        </div>
        """
        )
        for label, score in score_rows
    )
    related_markup = build_related_distro_cards(distro, all_distros)

    target_markup = "".join(
        f'<span class="user-pill">{safe_text(user)}</span>' for user in target_users
    )
    best_markup = "".join(f"<li>{safe_text(item)}</li>" for item in best_for)
    not_ideal_markup = "".join(f"<li>{safe_text(item)}</li>" for item in not_ideal)
    use_case_markup = "".join(f"<li>{safe_text(item)}</li>" for item in use_cases)

    keywords = [
        name,
        "Linux",
        "Distro",
        release_model,
        distro.get("category", ""),
        distro.get("package_manager", ""),
    ]
    meta_keywords = ", ".join(filter(None, keywords))

    screenshot_urls = screenshot_sources
    schema_logo = absolute_media_url(distro.get("logo") or distro.get("logo_source") or "")
    schema_app = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": "GNU/Linux",
        "name": name,
        "description": meta_description_text,
        "image": schema_logo,
        "url": f"{BASE_URL}/distros/{distro['id']}.html",
        "softwareVersion": str(distro.get("first_release", "")),
        "publisher": {"@type": "Organization", "name": "BESTLINUXDISTROS"},
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "releaseNotes": f"{release_model} cadence - {distro.get('status', 'Active')}",
        "downloadUrl": download_url or official_site,
        "screenshot": screenshot_urls,
        "keywords": keyword_terms,
    }
    schema_os = {
        "@context": "https://schema.org",
        "@type": "OperatingSystem",
        "name": name,
        "url": f"{BASE_URL}/distros/{distro['id']}.html",
        "description": meta_description_text,
        "operatingSystemType": family or "Linux",
        "screenshot": screenshot_urls,
        "softwareVersion": str(distro.get("first_release", "")),
        "image": f"{BASE_URL}/assets/og/{distro['id']}.png",
    }
    if distro.get("developer"):
        schema_app["provider"] = {"@type": "Organization", "name": distro["developer"]}
        schema_os["manufacturer"] = {"@type": "Organization", "name": distro["developer"]}
    schema_json = json.dumps([schema_app, schema_os], ensure_ascii=False)

    hero_logo = detail_logo_src(distro.get("logo", ""))
    domain = extract_domain(distro.get("website", ""))

    html_page = dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>{safe_text(name)} Linux Review | BESTLINUXDISTROS</title>
          <meta name="description" content="{meta_description}" />
          <meta name="keywords" content="{html.escape(meta_keywords)}" />
          <meta property="og:title" content="{safe_text(name)} Linux Review � BestLinuxDistros" />
          <meta property="og:description" content="{meta_description}" />
          <meta property="og:type" content="website" />
          <meta property="og:url" content="{BASE_URL}/distros/{distro['id']}.html" />
          <meta property="og:image" content="../assets/og/{distro['id']}.png" />
          <meta property="twitter:card" content="summary_large_image" />
          <link rel="canonical" href="{BASE_URL}/distros/{distro['id']}.html" />
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
          <link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" />
          <link rel="stylesheet" href="../css/styles.css" />
          <script type="application/ld+json">
          {schema_json}
          </script>
        </head>
        <body class="page detail" data-distro="{distro['id']}">
          <header class="site-header floating">
            <div class="logo-mark"><a href="../index.html">bestlinuxdistros<span class="dot">.com</span></a></div>
            <button class="nav-toggle" id="navToggle" aria-expanded="false" aria-label="Toggle navigation" aria-controls="site-nav">
              <span></span><span></span><span></span>
            </button>
            <nav class="primary-nav" id="site-nav">
              <a href="../index.html">Home</a>
              <a href="../distros.html">Distros</a>
              <a href="../compare.html">Compare</a>
              <a href="../blog/index.html">Blog</a>
              <a href="../index.html#guides">Guides</a>
              <a href="../index.html#tools">Tools</a>
              <a href="../distros.html#search" data-nav-search>Search</a>
            </nav>
          </header>
          <main class="detail-main">
            <a class="back-link" href="../distros.html">&larr; Back to catalog</a>
            <section class="detail-card detail-hero">
              <div class="hero-stack">
                <div class="hero-logo" data-name="{safe_text(name)}">
                  <img src="{html.escape(hero_logo)}" alt="{safe_text(name)} logo" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-domain="{html.escape(domain)}" />
                </div>
                <div class="hero-content">
                  <div class="eyebrow">{category_markup}</div>
                  <h1>{safe_text(name)}</h1>
                  <p class="lede">{lede_copy}</p>
                  {f'<div class="distro-tag-badges">{badge_chip_markup}</div>' if badge_chip_markup else ''}
                  <div class="badge-row">
                    <span class="status-badge" data-status="{status}">{status}</span>
                    {badge_markup}
                  </div>
                  <div class="hero-meta-grid">
                    {hero_meta_markup}
                  </div>
                  <div class="hero-actions">
                    {hero_actions_markup}
                  </div>
                </div>
              </div>
            </section>
            <nav class="breadcrumb">
              <a href="../index.html">Home</a>
              <span>&rsaquo;</span>
              <a href="../distros.html">Distros</a>
              <span>&rsaquo;</span>
              <span>{safe_text(name)}</span>
            </nav>
            <section class="detail-card overview-panel">
              <div class="section-heading">
                <h2>Overview</h2>
                <p>This snapshot highlights the {safe_text(release_model)} cadence, default desktop, and tooling so you know what to expect before installing.</p>
              </div>
              <div class="info-grid">
                {info_markup}
              </div>
            </section>
            <section class="detail-card audience-panel">
              <h2>Audience fit</h2>
              <div class="user-badges">
                {target_markup or '<span class="user-pill muted">General purpose installs</span>'}
              </div>
              <div class="compat-grid">
                <article>
                  <h3>Best suited for</h3>
                  <ul>{best_markup or '<li>General purpose desktops</li>'}</ul>
                </article>
                <article>
                  <h3>Consider alternatives if</h3>
                  <ul>{not_ideal_markup or '<li>Very old or low-power hardware</li>'}</ul>
                </article>
                <article>
                  <h3>Common deployments</h3>
                  <ul>{use_case_markup or '<li>Daily driver workloads</li>'}</ul>
                </article>
              </div>
            </section>
            <section class="detail-card pros-cons">
              <div>
                <h3>Pros</h3>
                <ul>{pros_markup}</ul>
              </div>
              <div>
                <h3>Cons</h3>
                <ul>{cons_markup}</ul>
              </div>
            </section>
            <section class="detail-card hardware-panel">
              <h2>Hardware requirements</h2>
              <table class="hw-table">
                <thead>
                  <tr>
                    <th>Spec</th>
                    <th>Minimum</th>
                    <th>Recommended</th>
                  </tr>
                </thead>
                <tbody>
                  {hw_markup}
                </tbody>
              </table>
            </section>
            <section class="detail-card package-panel">
              <h2>Package manager &amp; ecosystem</h2>
              <p class="package-name">{package_name}</p>
              <p>{package_blurb}</p>
            </section>
            <section class="detail-card screenshots-panel">
              <div class="section-heading">
                <h2>Screenshots</h2>
                <p>Tap or click to open full-size UI captures.</p>
              </div>
              <div class="screenshots-grid">
                {screenshot_markup or '<p class="muted">Screenshots coming soon.</p>'}
              </div>
            </section>
            <section class="detail-card benchmark-panel">
              <h2>Benchmarks &amp; signals</h2>
              <div class="benchmark-grid">
                <article>
                  <p class="muted-label">Boot time</p>
                  <span class="pill soft">{safe_text(boot_time)}</span>
                </article>
                <article>
                  <p class="muted-label">Resource usage</p>
                  <span class="pill soft">{safe_text(resource_usage)}</span>
                </article>
              </div>
              <div class="score-list">
                {score_markup}
              </div>
            </section>
            {related_markup}
            <a class="back-link bottom" href="../distros.html">&larr; Back to catalog</a>
          </main>
          <footer class="site-footer">
            <div>
              <p>Made by Saif &middot;  </p>
              <p class="last-updated" data-last-updated="{last_updated}">Last updated {last_updated}</p>
            </div>
            <div class="footer-links">
              <a href="../index.html#about">About</a>
              <a href="mailto:hello@bestlinuxdistros.com">Contact</a>
              <a href="../index.html#privacy">Privacy</a>
              <a href="../sitemap.xml">Sitemap</a>
              <a href="https://github.com/bestlinuxdistros" target="_blank" rel="noopener">GitHub</a>
            </div>
            <p class="footer-note">&copy; 2025 BestLinuxDistros.com &mdash; Open-Source Project. Made for Linux users, by Linux users.</p>
          </footer>
          <script src="../js/distro-data.js" defer></script>
          <script src="../js/app.js" defer></script>
          <script src="../js/detail.js" defer></script>
        </body>
        </html>
        """
    )
    return html_page


def build_badges(distro: dict, release_model: str) -> list[str]:
    badges: list[str] = []
    category = (distro.get("category") or "").lower()
    if (
        "beginner" in category
        or distro["id"] in BEGINNER_HINTS
        or int(distro.get("benchmarks", {}).get("beginner_score", 0)) >= 8
    ):
        badges.append("Beginner")
    if "server" in category or distro["id"] in SERVER_HINTS:
        badges.append("Server")
    if "security" in category or distro["id"] in SECURITY_HINTS:
        badges.append("Security")
    if release_model in {"LTS", "Rolling"}:
        badges.append(release_model)
    return dedupe_list(badges)


def split_badges(raw: str) -> list[str]:
    parts = []
    for chunk in raw.replace("/", ",").split(","):
        cleaned = chunk.strip()
        if cleaned:
            parts.append(cleaned)
    return parts or ["Curated distro"]


def dedupe_list(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def normalize_url(value: str) -> str:
    if not value:
        return ""
    trimmed = value.strip()
    if not trimmed:
        return ""
    if trimmed.startswith("//"):
        return f"https:{trimmed}"
    parsed = urlparse(trimmed)
    if parsed.scheme:
        return trimmed
    return f"https://{trimmed}"


def ensure_local_logo(distro_id: str, logo_url: str, website: str = "", display_name: str | None = None) -> str:
    cleaned = (logo_url or "").strip()
    sources: list[tuple[str, str]] = []
    if cleaned:
        sources.append((cleaned, infer_logo_suffix(cleaned)))
    domain = extract_domain(website or "")
    if domain:
        sources.append((f"{CLEARBIT_BASE}{domain}", ".png"))
    if not sources:
        return build_logo_placeholder(distro_id, display_name or distro_id)
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    for source_url, suffix in sources:
        filename = f"{distro_id}{suffix}"
        target = LOGO_DIR / filename
        rel_path = f"assets/logos/{filename}"
        if target.exists() and target.stat().st_size > 0:
            return rel_path
        try:
            req = Request(source_url, headers=UA_HEADER)
            with urlopen(req, timeout=15) as response:
                data = response.read()
            target.write_bytes(data)
            return rel_path
        except Exception as exc:
            print(f"[BLD] Failed to cache logo for {distro_id} from {source_url}: {exc}")
            continue
    return build_logo_placeholder(distro_id, display_name or distro_id)


def infer_logo_suffix(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in LOGO_SUFFIXES:
        return suffix
    return ".svg"


def build_logo_placeholder(distro_id: str, name: str) -> str:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{distro_id}-placeholder.png"
    target = LOGO_DIR / filename
    rel_path = f"assets/logos/{filename}"
    if target.exists() and target.stat().st_size > 0:
        return rel_path
    if Image is None:
        target.write_bytes(BLANK_PNG)
        return rel_path
    size = 256
    canvas = Image.new("RGBA", (size, size), "#050914")
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((0, 0, size, size), fill="#111835")
    initials = "".join(word[0] for word in (name or distro_id).split() if word)[:2].upper()
    if not initials:
        initials = distro_id[:2].upper()
    font = choose_font(120)
    try:
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        text_w, text_h = draw.textsize(initials, font=font)
    draw.text(
        ((size - text_w) / 2, (size - text_h) / 2),
        initials,
        font=font,
        fill=(51, 255, 87, 255),
    )
    canvas.convert("RGBA").save(target, "PNG", optimize=True)
    return rel_path


def detail_logo_src(path: str) -> str:
    if not path:
        return ""
    trimmed = path.strip()
    if not trimmed:
        return ""
    if trimmed.startswith(("http://", "https://", "data:")):
        return trimmed
    if trimmed.startswith("../"):
        return trimmed
    return f"../{trimmed.lstrip('./')}"


def absolute_media_url(path: str) -> str:
    if not path:
        return ""
    trimmed = path.strip()
    if not trimmed:
        return ""
    if trimmed.startswith(("http://", "https://")):
        return trimmed
    return f"{BASE_URL}/{trimmed.lstrip('./')}"


def safe_text(value: object) -> str:
    return html.escape(str(value)) if value is not None else ""


def extract_domain(url: str) -> str:
    try:
        hostname = urlparse(url).hostname or ""
        return hostname.replace("www.", "")
    except ValueError:
        return ""


def write_snapshot(
    distros: list[dict], generated_at: str, last_updated_display: str
) -> None:
    payload = {
        "generatedAt": generated_at,
        "lastUpdatedDisplay": last_updated_display,
        "distros": distros,
    }
    json_blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    js_body = f"window.__BLD_DATA__={json_blob};"
    SNAPSHOT_PATH.write_text(js_body, encoding="utf-8")


def write_sitemap(distros: list[dict], lastmod: str) -> None:
    urls = [
        ("", lastmod),
        ("/index.html", lastmod),
        ("/distros.html", lastmod),
        ("/compare.html", lastmod),
        ("/blog/index.html", lastmod),
        ("/blog/best-linux-distros-for-beginners-2025.html", lastmod),
        ("/blog/best-linux-distros-for-developers-and-programmers-2025.html", lastmod),
        ("/blog/best-lightweight-linux-distros-for-old-laptops-2025.html", lastmod),
        ("/blog/best-rolling-release-linux-distros-2025.html", lastmod),
        ("/blog/best-linux-distros-for-gaming-and-steam-deck-2025.html", lastmod),
        ("/blog/best-linux-distros-for-servers-and-cloud-2025.html", lastmod),
        ("/blog/best-linux-distros-for-security-and-penetration-testing-2025.html", lastmod),
        ("/blog/best-linux-distros-for-data-science-and-ai-2025.html", lastmod),
        ("/blog/best-linux-distros-for-designers-and-creatives-2025.html", lastmod),
        ("/blog/homelab-linux-distros-and-tools-2025.html", lastmod),
        ("/blog/best-linux-distros-for-privacy-and-anonymity-2025.html", lastmod),
        ("/blog/best-linux-distros-for-raspberry-pi-and-arm-2025.html", lastmod),
        ("/blog/linux-distros-for-educators-and-classrooms-2025.html", lastmod),
        ("/guides/index.html", lastmod),
        ("/guides/linux-beginners-guide-2025.html", lastmod),
        ("/guides/linux-security-hardening-2025.html", lastmod),
        ("/guides/how-to-choose-a-linux-distro.html", lastmod),
        ("/guides/linux-performance-tuning-2025.html", lastmod),
        ("/tools/index.html", lastmod),
        ("/tools/hardware-compatibility-checker.html", lastmod),
        ("/tools/package-manager-cheatsheet.html", lastmod),
        ("/tools/kernel-update-guide.html", lastmod),
        ("/tools/linux-filesystem-explained.html", lastmod),
    ]
    for distro in distros:
        urls.append((f"/distros/{distro['id']}.html", lastmod))
    urlset = "\n".join(
        f"  <url><loc>{BASE_URL}{path}</loc><lastmod>{lastmod}</lastmod></url>"
        for path, lastmod in urls
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urlset}
</urlset>
"""
    SITEMAP_PATH.write_text(xml, encoding="utf-8")


def build_related_distro_cards(distro: dict, distros: list[dict], limit: int = 3) -> str:
    current_id = distro["id"]
    current_family = (distro.get("family") or "").lower()
    current_badges = {b.lower() for b in (distro.get("badges") or [])}
    scored: list[tuple[float, dict]] = []
    for other in distros:
        if other["id"] == current_id:
            continue
        score = 0.0
        if current_family and (other.get("family") or "").lower() == current_family:
            score += 2.0
        other_badges = {b.lower() for b in (other.get("badges") or [])}
        score += len(current_badges & other_badges)
        if score > 0:
            scored.append((score, other))
    if len(scored) < limit:
        existing_ids = {other["id"] for _, other in scored} | {current_id}
        for other in sorted(distros, key=lambda item: item.get("popularity_rank", 999)):
            if other["id"] in existing_ids:
                continue
            scored.append((0.1, other))
            existing_ids.add(other["id"])
            if len(scored) >= limit + 3:
                break
    scored.sort(key=lambda item: (-item[0], item[1].get("popularity_rank", 999)))
    related = [entry for _, entry in scored[:limit]]
    if not related:
        return ""
    cards = "".join(
        f"""
                <article class="distro-card">
                  <div class="distro-logo">
                    <img src="{html.escape(detail_logo_src(other.get('logo', '')))}" alt="{safe_text(other.get('name'))} logo" loading="lazy" decoding="async" referrerpolicy="no-referrer" />
                  </div>
                  <h3>{safe_text(other.get('name'))}</h3>
                  <p class="muted-label">{safe_text(other.get('family') or other.get('category') or '')}</p>
                  <a class="link-arrow" href="../distros/{other['id']}.html">View details &rsaquo;</a>
                </article>
        """
        for other in related
    )
    return f"""
            <section class="detail-card related-panel">
              <div class="section-heading">
                <h2>You may also like</h2>
                <p>Explore similar distributions with shared traits.</p>
              </div>
              <div class="related-grid">
                {cards}
              </div>
            </section>
    """


def generate_og_image(distro: dict, screenshots: list[str]) -> None:
    OG_DIR.mkdir(parents=True, exist_ok=True)
    target = OG_DIR / f"{distro['id']}.png"
    if Image is None:
        fallback_og_image(target, screenshots)
        return
    width, height = 1200, 630
    canvas = Image.new("RGBA", (width, height), "#050914")
    if screenshots:
        try:
            req = Request(screenshots[0], headers=UA_HEADER)
            with urlopen(req, timeout=10) as response:
                raw = response.read()
            shot = Image.open(BytesIO(raw)).convert("RGB")
            shot = shot.resize((width, height), Image.LANCZOS)
            shot = shot.filter(ImageFilter.GaussianBlur(radius=18))
            canvas = shot.convert("RGBA")
        except Exception:
            pass
    overlay = Image.new("RGBA", (width, height), (5, 9, 25, 200))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)
    title_font = choose_font(78)
    subtitle_font = choose_font(34)
    title = distro.get("name", "").upper()
    try:
        bbox = draw.textbbox((0, 0), title, font=title_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        text_w, text_h = draw.textsize(title, font=title_font)
    text_x = (width - text_w) / 2
    text_y = (height - text_h) / 2
    glow_color = (51, 255, 87, 160)
    for offset in (-3, -2, 2, 3):
        draw.text((text_x + offset, text_y + offset), title, font=title_font, fill=glow_color)
    draw.text((text_x, text_y), title, font=title_font, fill=(236, 244, 255, 255))
    subtitle = "bestlinuxdistros.com"
    try:
        sub_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_w = sub_box[2] - sub_box[0]
    except AttributeError:
        sub_w, _ = draw.textsize(subtitle, font=subtitle_font)
    draw.text(
        (width / 2 - sub_w / 2, height * 0.75),
        subtitle,
        font=subtitle_font,
        fill=(140, 255, 210, 220),
    )
    canvas.convert("RGB").save(target, "PNG", quality=90, optimize=True)


def choose_font(size: int):
    for name in ("Arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def fallback_og_image(target: Path, screenshots: list[str]) -> None:
    try:
        if screenshots:
            req = Request(screenshots[0], headers=UA_HEADER)
            with urlopen(req, timeout=10) as response:
                data = response.read()
            target.write_bytes(data)
        else:
            target.write_bytes(BLANK_PNG)
    except Exception:
        target.write_bytes(BLANK_PNG)


def fetch_wiki_screenshots(page_title: str) -> list[str]:
    """
    Fetch up to 6 screenshots for a distro using Wikipedia API + Wikimedia FilePath.
    Only returns PNG/JPG images.
    """
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "images",
        "gimlimit": "max",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url",
        "titles": page_title,
    }

    try:
        url = f"{api_url}?{urlencode(params)}"
        req = Request(url, headers=UA_HEADER)
        with urlopen(req, timeout=10) as response:
            data = json.load(response)
    except Exception:
        return []

    screenshots: list[str] = []
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        title = page.get("title", "")
        lower = title.lower()
        if lower.endswith((".png", ".jpg", ".jpeg")) and "logo" not in lower and "icon" not in lower:
            imageinfo = page.get("imageinfo")
            if not imageinfo:
                continue
            url = imageinfo[0].get("url")
            if not url:
                continue
            screenshots.append(url)
            print(f"[BLD] Screenshot: {url}")
            if len(screenshots) == 6:
                break
    return screenshots


def build_placeholder_screenshots(name: str) -> list[str]:
    encoded = quote_plus(name or "Linux")
    return [
        f"https://dummyimage.com/800x450/13142a/33ff57&text={encoded}+Desktop",
        f"https://dummyimage.com/800x450/0b0c18/f0f6ff&text={encoded}+Apps",
    ]


if __name__ == "__main__":
    main()





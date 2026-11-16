"""Check the hosted page, manifest, source catalogue and no-JavaScript behavior."""

import argparse
import re
from pathlib import Path
from shutil import copytree
from struct import unpack_from
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit

from browser_checks import TEMP, chrome, write_report
from build_atlas import build
from check_navigation import wait_for_section
from preview_atlas import preview_server, project_path
from read_sources import read_sources
from site_files import MANIFEST, ROOT, read_site_file_types

SOURCE_TITLE = "Stanford / Liu et al., 2018"
SOURCE_ENTRY = "#source-arch"
HISTORY = "#history-old"
FOCUSED = "element => document.activeElement === element"
ASSET_TYPES = {"script", "stylesheet", "image", "font", "fetch", "xhr", "manifest"}

PAGE_STATE = r"""() => ({
    title: document.title,
    h1: document.querySelector('h1').innerText.replace(/\s+/g, ' ').trim(),
    charset: document.characterSet,
    main: document.querySelectorAll('main').length,
    styles: document.querySelectorAll('.style-card').length,
    sources: document.querySelectorAll('.source-entry').length,
    text: document.body.innerText,
    localLinks: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'))
        .filter(h => !h.startsWith('#') && !/^https?:/.test(h)),
})"""

SOURCE_ENTRIES = """entries => entries.map(source => {
    const button = source.querySelector('.source-trigger');
    const dialog = document.getElementById(button?.getAttribute('popovertarget'));
    return {
        id: source.id, isAutoPopover: dialog?.matches('dialog[popover="auto"]'),
        title: document.getElementById(dialog?.getAttribute('aria-labelledby'))?.textContent,
        note: dialog?.querySelector('p')?.textContent,
        originalLink: dialog?.querySelector('a[target="_blank"]')?.getAttribute('href'),
        fallbackLink: source.querySelector('.source-fallback')?.getAttribute('href'),
    };
})"""


def source_record(number, source_id, url="https://example.org/"):
    return f"\n## {number} · {source_id}\n\n- Название: {source_id}\n- Ссылка: <{url}>\n- Группа: История\n\nЗапись для регрессионной проверки.\n"


def build_fixture(records):
    with TemporaryDirectory(prefix="sources-check-", dir=TEMP) as directory:
        fixture = Path(directory)
        copytree(ROOT / "assets", fixture / "assets")
        with (fixture / "assets/beer-sources.md").open(
            "a", encoding="utf-8", newline="\n"
        ) as catalogue:
            catalogue.write(records)
        build(fixture)
        return (fixture / "index.html").read_text(encoding="utf-8")


def check_source_ids(browser):
    page = browser.new_page(java_script_enabled=False)
    try:
        page.set_content(
            build_fixture(
                source_record(1000001, "arch-title") + source_record(1000002, "popover-arch")
            )
        )
        for source_id, title in (
            ("arch", SOURCE_TITLE),
            ("arch-title", "arch-title"),
            ("popover-arch", "popover-arch"),
        ):
            button = page.locator(f"#source-{source_id} > .source-trigger")
            dialog = page.get_by_role("dialog", name=title, exact=True)
            button.press("Enter")
            assert dialog.is_visible(), f"Source {source_id} must open its own dialog without JS"
            page.keyboard.press("Escape")
            assert not dialog.is_visible()
    finally:
        page.context.close()
    try:
        build_fixture(source_record(1000003, "relative-url", "https:example.org"))
    except ValueError as error:
        assert re.search(r"absolute HTTP\(S\) URL.*relative-url", str(error)), error
    else:
        raise AssertionError("Accepted an ambiguous URL instead of an absolute source URL")


def link_to_entry(page):
    return page.get_by_role("dialog", name=SOURCE_TITLE).get_by_role(
        "link", name="К записи в атласе"
    )


def assert_entry_is_tappable(page):
    page.wait_for_url(lambda url: urlsplit(url).fragment == SOURCE_ENTRY[1:], timeout=3000)
    title = page.locator(SOURCE_ENTRY + " .source-trigger")
    assert title.evaluate("""button => {
        const rect = button.getBoundingClientRect();
        return button.contains(document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2));
    }"""), "Source title must be tappable after navigation"


def open_source_tab(page):
    with page.expect_popup(timeout=3000) as popup:
        link_to_entry(page).tap()
    destination = popup.value
    assert_entry_is_tappable(destination)
    return destination


def check_source_jump(browser, base, javascript):
    page = browser.new_page(
        java_script_enabled=javascript,
        viewport={"width": 320, "height": 568 if javascript else 360},
        is_mobile=True,
        has_touch=True,
        reduced_motion="reduce",
    )
    try:
        page.goto(base + HISTORY)
        citation = page.locator(HISTORY + " .source-trigger").first
        citation.tap()
        if not javascript:
            destination = open_source_tab(page)
            destination.locator(SOURCE_ENTRY + " .source-trigger").tap()
            open_source_tab(destination).close()
            destination.close()
            return

        position = page.evaluate("scrollY")
        link_to_entry(page).tap()
        assert_entry_is_tappable(page)
        page.go_back()
        page.wait_for_url(lambda url: urlsplit(url).fragment == HISTORY[1:])
        page.wait_for_function("y => Math.abs(scrollY - y) <= 2", arg=position, timeout=1500)
        assert citation.evaluate(FOCUSED), "Back should return focus to the citation"
        page.go_forward()
        assert_entry_is_tappable(page)
        page.set_viewport_size({"width": 667, "height": 375})
        page.go_back()
        assert citation.evaluate("""button => {
            const rect = button.getBoundingClientRect();
            const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
            return document.activeElement === button && button.contains(hit);
        }"""), "Back after rotation should restore the same visible citation"
    finally:
        page.context.close()


def check_manifest(page, base, title):
    links = page.locator(
        'head link:is([rel="icon"],[rel="apple-touch-icon"],[rel="manifest"])'
    ).evaluate_all(
        "links => links.map(link => [link.rel, link.getAttribute('href'), link.type, link.getAttribute('sizes')])"
    )
    assert links == [
        ["icon", "favicon.ico", "", "32x32"],
        ["icon", "icon.svg", "image/svg+xml", None],
        ["apple-touch-icon", "apple-touch-icon.png", "", "180x180"],
        ["manifest", MANIFEST, "", None],
    ], links
    manifest_url = urljoin(base, MANIFEST)
    response = page.request.get(manifest_url)
    assert response.ok and response.headers["content-type"].startswith("application/manifest+json")
    manifest = response.json()
    assert manifest["name"] == title and manifest["display"] == "standalone"
    for key in ("start_url", "scope", "id"):
        assert urljoin(manifest_url, manifest[key]) == base, key
    assert [(icon["sizes"], icon.get("purpose", "any")) for icon in manifest["icons"]] == [
        ("192x192", "any"),
        ("512x512", "maskable"),
        ("512x512", "any"),
    ]
    apple = {"src": "apple-touch-icon.png", "type": "image/png", "sizes": "180x180"}
    for icon in [*manifest["icons"], apple]:
        url = urljoin(manifest_url, icon["src"])
        assert url.startswith(base) and icon["type"] == "image/png", icon
        response = page.request.get(url)
        assert response.ok and response.headers["content-type"] == "image/png", url
        png = response.body()
        assert (
            png[:8] == b"\x89PNG\r\n\x1a\n"
            and "%dx%d" % unpack_from(">II", png, 16) == icon["sizes"]
        ), url
    svg = page.request.get(urljoin(base, "icon.svg"))
    assert svg.ok and svg.headers["content-type"] == "image/svg+xml"
    ico = page.request.get(urljoin(base, "favicon.ico"))
    assert ico.ok and ico.headers["content-type"] == "image/vnd.microsoft.icon"
    data = ico.body()
    assert data[:8] == bytes((0, 0, 1, 0, 1, 0, 32, 32))
    assert unpack_from("<H", data, 12) == (32,)
    size, offset = unpack_from("<II", data, 14)
    dib_size = unpack_from("<I", data, offset)[0]
    pixels = 32 * 32 * 4
    assert size == dib_size + pixels + 4 * 32 and len(data) == offset + size
    assert any(data[offset + dib_size + pixels :])


def check_metadata(page, title):
    canonical = "https://ntishkevich.github.io/dive-into-beer/"

    def meta(attribute, key):
        return page.locator(f'head meta[{attribute}="{key}"]').get_attribute("content")

    assert page.locator('head link[rel="canonical"]').evaluate_all(
        "links => links.map(link => link.href)"
    ) == [canonical]
    description = meta("name", "description")
    assert description
    assert page.locator('meta[name="keywords"]').count() == 1 and "история пива" in meta(
        "name", "keywords"
    )
    expected = {
        "og:url": canonical,
        "og:title": title,
        "og:type": "website",
        "og:description": description,
        "og:image": urljoin(canonical, "assets/social-cover.jpg"),
        "og:image:type": "image/jpeg",
        "og:image:width": "1200",
        "og:image:height": "630",
    }
    for key, value in expected.items():
        assert meta("property", key) == value, key
    assert meta("property", "og:image:alt")
    assert meta("name", "robots") == "max-image-preview:large"
    assert meta("name", "twitter:card") == "summary_large_image"


def check_keyboard(page, base):
    page.set_viewport_size({"width": 320, "height": 480})
    page.emulate_media(reduced_motion="reduce")
    page.goto(base + HISTORY)
    citations = page.locator(HISTORY + " .source-trigger")
    dialog = page.get_by_role("dialog", name=SOURCE_TITLE)
    citations.first.press("Enter")
    assert dialog.is_visible()
    page.keyboard.press("Tab")
    assert dialog.get_by_role("link", name=re.compile("Открыть в новой вкладке")).evaluate(FOCUSED)
    page.keyboard.press("Tab")
    assert link_to_entry(page).evaluate(FOCUSED)
    page.keyboard.press("Tab")
    dialog.wait_for(state="hidden", timeout=3000)
    assert citations.nth(1).evaluate(FOCUSED)


def check_static_content(page, base, sources):
    assert page.locator(".style-card").count() == 22
    assert page.locator(".source-entry").count() == len(sources)
    assert page.locator(".atlas-sidebar a").count() == 11
    page.get_by_role("link", name="Хмель. Перейти к IPA и APA").press("Enter")
    assert urlsplit(page.url).fragment == "hops"
    page.goto(base + HISTORY)
    citation = page.locator(HISTORY + " .source-trigger").first
    citation.press("Enter")
    dialog = page.get_by_role("dialog", name=SOURCE_TITLE)
    assert dialog.is_visible() and link_to_entry(page).get_attribute("href") == SOURCE_ENTRY
    page.keyboard.press("Escape")
    assert not dialog.is_visible() and citation.evaluate(FOCUSED)
    entries = page.locator("#sources .source-entry").evaluate_all(SOURCE_ENTRIES)
    assert entries == [
        {
            "id": "source-" + source["id"],
            "isAutoPopover": True,
            "title": source["title"],
            "note": source["note"],
            "originalLink": source["url"],
            "fallbackLink": source["url"],
        }
        for source in sources
    ]
    bibliography = page.get_by_role("button", name=f"01 {SOURCE_TITLE}")
    bibliography.press("Enter")
    assert dialog.is_visible()
    page.keyboard.press("Escape")
    assert not dialog.is_visible() and bibliography.evaluate(FOCUSED)
    page.emulate_media(media="print")
    assert (
        page.locator(SOURCE_ENTRY + " .source-fallback").is_visible()
        and not bibliography.is_visible()
    )


def main(argv=None):
    argparse.ArgumentParser(
        description="Check the hosted site and sources without JavaScript."
    ).parse_args(argv)
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    sources = read_sources()
    with preview_server() as origin, chrome() as browser:
        base = origin + project_path()
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        errors, assets = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        icon_urls = {
            urljoin(base, name)
            for name in read_site_file_types((ROOT / MANIFEST).read_bytes())
            if name not in {"index.html", "assets/social-cover.jpg"}
        }

        def collect_asset(request):
            if request.resource_type in ASSET_TYPES and request.url not in icon_urls:
                assets.append(request.url)

        page.on("request", collect_asset)
        page.goto(base + "#map")
        wait_for_section(page, "map")
        state = page.evaluate(PAGE_STATE)
        assert state["title"] == state["h1"] == "Погружение в ПИВАС"
        assert state["charset"] == "UTF-8" and state["main"] == 1
        assert state["styles"] == 22 and state["sources"] == len(sources)
        assert page.locator(".atlas-sidebar").count() == 1
        assert page.locator(".prototype-switcher,[data-variant-step],.reading-chapter").count() == 0
        assert not ("data-prototype" in html or "data-variant" in html)
        assert not re.search(
            r"Русский язык|Источники проверены|преподавател|в чате|Твоя цель|Сначала раздели\s|\uFFFD",
            state["text"],
            re.IGNORECASE,
        ), "Private lesson copy remains"
        assert not state["localLinks"] and not assets and not errors, (
            state["localLinks"],
            assets,
            errors,
        )
        page.locator(".brand").click()
        wait_for_section(page, "start")
        page.screenshot(path=TEMP / "public-desktop.png")
        page.set_viewport_size({"width": 360, "height": 900})
        page.goto(base + "#map")
        wait_for_section(page, "map")
        page.screenshot(path=TEMP / "public-mobile.png")
        check_keyboard(page, base)

        static = browser.new_page(java_script_enabled=False)
        static.goto(base)
        check_manifest(static, base, state["title"])
        check_metadata(static, state["title"])
        check_static_content(static, base, sources)
        check_source_ids(browser)
        for javascript in (True, False):
            check_source_jump(browser, base, javascript)
    assert not errors and not assets, (errors, assets)
    write_report(
        "static-site-check.json",
        {
            "projectSubpath": True,
            "title": state["title"],
            "profiles": state["styles"],
            "sources": len(sources),
            "externalAssetRequests": assets,
            "privateLessonCopy": False,
            "prototypeControls": False,
            "staticOutline": True,
            "readableWithoutJavaScript": True,
            "coverLinksWithoutJavaScript": True,
            "sourcePopoverWithoutJavaScript": True,
            "sourceJumpWithoutJavaScript": True,
            "sourceJumpRestoresReadingPosition": True,
            "bibliographyPopovers": len(sources),
            "errors": errors,
        },
    )


if __name__ == "__main__":
    main()

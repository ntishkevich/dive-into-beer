"""Check the chapter numbering, sticky header and native browser history."""

import argparse

from browser_checks import TEMP, chrome, write_report
from site_files import ROOT

SECTIONS = (
    ("start", "start", "Начало"),
    ("map", "start", "Карта понятий"),
    ("history-old", "history-old", "Древность"),
    ("history-new", "history-old", "крафту"),
    ("history-regional", "history-old", "Россия и Беларусь"),
    ("school-central", "school-central", "Германия"),
    ("school-belgium", "school-central", "Бельгия"),
    ("school-islands", "school-central", "Ирландия"),
    ("school-america", "school-central", "США"),
    ("school-russia", "school-central", "Россия"),
    ("school-belarus", "school-central", "Беларусь"),
    ("hops", "hops", "IPA"),
    ("sour", "sour", "Гозе"),
    ("wild", "sour", "Ламбик"),
    ("lagers", "lagers", "Лагеры"),
    ("yeasty", "lagers", "Пшеница"),
    ("dark", "lagers", "Портер"),
    ("brew", "brew", "Пивоварение"),
    ("label", "label", "Этикетки"),
    ("myths", "myths", "байки"),
    ("myths-inspectors", "myths", "штаны"),
    ("myths-cities", "myths", "Пльзень"),
    ("myths-culture", "myths", "Нинкаси"),
    ("myths-brief", "myths", "Короткие ответы"),
    ("quick", "myths", "Шпаргалка"),
    ("practice", "practice", "Самопроверка"),
    ("sources", "sources", "Источники"),
)

NUMBERING = """() => [...document.querySelectorAll('.atlas-sidebar a')].map(link => ({
    menu: link.querySelector('span').textContent.trim(),
    sections: [...document.querySelectorAll('.sheet[data-nav-group]')]
        .filter(section => section.id !== 'start' && section.dataset.navGroup === link.dataset.sectionLink)
        .map(section => ({
            id: section.id,
            heading: section.querySelector('.eyebrow').textContent.trim().split(' / ')[0],
            footer: section.querySelector('.chapter-footer span:last-child')?.textContent.trim(),
        })),
}))"""

LAYOUT = """() => {
    const nav = document.querySelector('.topnav').getBoundingClientRect();
    const section = document.getElementById('school-central').getBoundingClientRect();
    const title = document.querySelector('[data-current-section-title]').getBoundingClientRect();
    return {
        width: innerWidth, documentWidth: document.documentElement.scrollWidth,
        headerHeight: nav.height, headerTop: nav.top, sectionTop: section.top,
        titleRight: title.right, titleBottom: title.bottom, headerBottom: nav.bottom,
    };
}"""


def wait_for_section(page, section):
    page.wait_for_function(
        "id => document.querySelector('.topnav').dataset.currentSection === id", arg=section
    )


def scroll_to(page, section, gap=20):
    page.evaluate(
        """([id, gap]) => {
            const element = document.getElementById(id);
            const header = document.querySelector('.topnav').getBoundingClientRect();
            window.scrollTo({top: element.getBoundingClientRect().top + scrollY - header.height - gap,
                             behavior: 'instant'});
        }""",
        [section, gap],
    )


def check_numbering(page):
    chapters = page.evaluate(NUMBERING)
    for i, chapter in enumerate(chapters, 1):
        menu = f"{i:02}"
        assert chapter["menu"] == menu, chapter
        for j, section in enumerate(chapter["sections"], 1):
            number = f"{menu}.{j}" if len(chapter["sections"]) > 1 else menu
            assert section["heading"] == number and section["footer"] == f"РАЗДЕЛ {number}", section
    assert sum(len(chapter["sections"]) for chapter in chapters) == len(SECTIONS) - 1
    for selector in (".header-index", ".atlas-mobile-index"):
        copy = page.locator(selector + " a span").all_text_contents()
        assert [part.strip() for part in copy] == [chapter["menu"] for chapter in chapters]
    return chapters


def main(argv=None):
    argparse.ArgumentParser(
        description="Check chapter navigation and responsive anchors."
    ).parse_args(argv)
    url = (ROOT / "index.html").as_uri()
    errors = []
    with chrome() as browser:
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.emulate_media(reduced_motion="reduce")
        page.goto(url)
        numbering = check_numbering(page)
        for section, group, label in SECTIONS:
            scroll_to(page, section)
            wait_for_section(page, section)
            active = page.locator(".atlas-sidebar a[aria-current]").evaluate_all(
                "links => links.map(link => link.getAttribute('href'))"
            )
            expected = "#map" if group == "start" else f"#{group}"
            assert active == [expected], f"Wrong active group for {section}: {active}"
            assert label in page.locator("[data-current-section-title]").text_content(), section

        scroll_to(page, "school-central", gap=27)
        wait_for_section(page, "history-regional")
        page.evaluate("window.scrollBy({top: 6, behavior: 'instant'})")
        wait_for_section(page, "school-central")
        page.evaluate("window.scrollBy({top: -6, behavior: 'instant'})")
        wait_for_section(page, "history-regional")
        layouts = []
        for width in (320, 360, 768, 1200):
            page.set_viewport_size({"width": width, "height": 900})
            if width <= 900:
                page.locator(".header-index summary").click()
                page.locator('.header-index a[href="#school-central"]').click()
            else:
                page.locator('.atlas-sidebar a[href="#school-central"]').click()
            wait_for_section(page, "school-central")
            layout = page.evaluate(LAYOUT)
            assert layout["documentWidth"] <= width + 1 and layout["headerHeight"] < 300, layout
            assert layout["sectionTop"] >= layout["headerBottom"] - 1, layout
            assert (
                layout["titleRight"] <= width and layout["titleBottom"] <= layout["headerBottom"]
            ), layout
            layouts.append(layout)
            if width in (360, 1200):
                page.screenshot(path=TEMP / f"navigation-{width}.png")

        for section in ("hops", "sour"):
            page.locator(f'.atlas-sidebar a[href="#{section}"]').click()
            wait_for_section(page, section)
        page.go_back()
        wait_for_section(page, "hops")
        page.go_forward()
        wait_for_section(page, "sour")
        page.set_viewport_size({"width": 360, "height": 900})
        page.locator(".header-index summary").click()
        page.keyboard.press("Escape")
        assert page.locator(".header-index").evaluate("menu => !menu.open"), (
            "Escape left the menu open"
        )
        page.goto(url + "#school-belgium")
        wait_for_section(page, "school-belgium")
        deep_link = page.evaluate("""() => ({
            headerBottom: document.querySelector('.topnav').getBoundingClientRect().bottom,
            sectionTop: document.getElementById('school-belgium').getBoundingClientRect().top,
        })""")
        assert deep_link["sectionTop"] >= deep_link["headerBottom"] - 1, deep_link
    assert not errors, errors
    write_report(
        "navigation-check.json",
        {
            "sectionsChecked": len(SECTIONS),
            "numbering": numbering,
            "boundaryBothDirections": True,
            "layouts": layouts,
            "deepLink": deep_link,
            "nativeHistory": True,
            "mobileMenuEscape": True,
            "errors": errors,
        },
    )


if __name__ == "__main__":
    main()

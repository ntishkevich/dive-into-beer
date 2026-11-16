"""Check the atlas layout at supported widths and with larger browser fonts."""

import argparse

from browser_checks import TEMP, chrome, write_report
from read_sources import read_sources
from site_files import ROOT

STRUCTURE = """() => ({
    chapters: document.querySelectorAll('.sheet').length,
    profiles: document.querySelectorAll('.style-card').length,
    sources: document.querySelectorAll('.source-entry').length,
    brokenAnchors: [...document.querySelectorAll('a[href^="#"]')]
        .map(a => a.getAttribute('href')).filter(h => !document.getElementById(h.slice(1))),
    externalAssets: document.querySelectorAll('script[src],link[rel="stylesheet"],img[src]').length,
})"""

LAYOUT = """() => {
    const heading = document.querySelector('.cover h1');
    const range = document.createRange();
    const coverRouteFits = [...document.querySelectorAll('.cover-route b,.cover-route span')]
        .every(element => {
            const cell = element.parentElement.getBoundingClientRect();
            range.selectNodeContents(element);
            return [...range.getClientRects()].every(
                rect => rect.left >= cell.left - 1 && rect.right <= cell.right + 1,
            );
        });
    const overflowingDates = [...document.querySelectorAll('.timeline__date')].filter(date => {
        range.selectNodeContents(date);
        return range.getBoundingClientRect().right > date.getBoundingClientRect().right + 1;
    }).map(date => date.textContent);
    range.selectNodeContents(heading);
    return {
        width: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        coverHeadingWidth: range.getBoundingClientRect().width,
        coverAvailable: heading.clientWidth,
        coverRouteFits,
        overflowingDates,
    };
}"""

ENLARGED_TIMELINE = """() => {
    const range = document.createRange();
    const rows = [...document.querySelectorAll('.timeline__event')];
    const overflowingRows = rows.filter(row => [...row.children].some(column => {
        range.selectNodeContents(column);
        return range.getBoundingClientRect().right > column.getBoundingClientRect().right + 1;
    })).map(row => row.querySelector('h3').textContent);
    return {fontSize: getComputedStyle(document.documentElement).fontSize,
            rowCount: rows.length, overflowingRows};
}"""


def main(argv=None):
    argparse.ArgumentParser(description="Check the atlas layout and exercises.").parse_args(argv)
    with chrome() as browser:
        page = browser.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "index.html").as_uri())
        structure = page.evaluate(STRUCTURE)
        layouts = []
        for width in (320, 360, 560, 561, 768, 1200, 1376):
            page.set_viewport_size({"width": width, "height": 900})
            layouts.append(page.evaluate(LAYOUT))

        page.set_viewport_size({"width": 1200, "height": 1000})
        for selector, name in (
            (".cover", "cover"),
            ("#hops", "hops"),
            ("#school-central", "schools-central"),
            ("#school-belgium", "schools-belgium"),
        ):
            page.locator(selector).screenshot(path=TEMP / f"{name}-browser.png")
        page.locator('#style-compare button[data-style="dipa"]').click()
        comparison = page.locator("[data-compare-output]").inner_text()
        quizzes = page.locator("[data-quiz]")
        quizzes.first.locator('button[data-choice="0"]').click()
        feedback = quizzes.first.locator(".quiz-feedback")
        correct_text = feedback.inner_text()
        correct_class = feedback.get_attribute("class")
        quizzes.nth(1).locator('button[data-choice="2"]').click()
        wrong_class = quizzes.nth(1).locator(".quiz-feedback").get_attribute("class")
        page.set_viewport_size({"width": 360, "height": 900})
        page.locator("#hops").screenshot(path=TEMP / "hops-mobile.png")
        page.context.new_cdp_session(page).send(
            "Page.setFontSizes", {"fontSizes": {"standard": 24}}
        )
        enlarged = []
        for width in (320, 561, 841):
            page.set_viewport_size({"width": width, "height": 900})
            enlarged.append(dict(width=width, **page.evaluate(ENLARGED_TIMELINE)))

    report = {
        "structure": structure,
        "layout": layouts,
        "enlargedTimeline": enlarged,
        "comparisonUpdated": "double ipa" in comparison.lower(),
        "correctFeedback": correct_text,
        "correctClass": correct_class,
        "wrongClass": wrong_class,
        "errors": errors,
    }
    write_report("browser-check.json", report)
    assert not errors, errors
    assert not structure["brokenAnchors"], structure
    assert structure["profiles"] == 22 and structure["sources"] == len(read_sources()), structure
    for state in layouts:
        assert state["documentWidth"] <= state["width"] + 1, state
        assert state["coverHeadingWidth"] <= state["coverAvailable"] + 1, state
        assert state["coverRouteFits"] and not state["overflowingDates"], state
    assert report["comparisonUpdated"] and "good" in correct_class and "bad" in wrong_class, report
    for state in enlarged:
        assert state["fontSize"] == "24px" and state["rowCount"] and not state["overflowingRows"], (
            state
        )


if __name__ == "__main__":
    main()

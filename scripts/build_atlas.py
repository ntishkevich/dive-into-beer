"""Build the standalone atlas and its web app manifest."""

import argparse
import json
import re
from urllib.parse import urljoin, urlsplit

from read_sources import read_sources
from site_files import MANIFEST, ROOT, read_json

ESCAPES = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})
QUICK_STYLES = (
    "helles",
    "pils",
    "apa",
    "ipa",
    "hazy",
    "gose",
    "gueuze",
    "weiss",
    "saison",
    "stout",
    "imperial",
)
COMPARE_STYLES = ("apa", "ipa", "hazy", "dipa")
THEME_COLOR = "#183b34"
NEW_TAB_DESCRIPTION = "atlas-source-new-tab"
QUIZ = (
    (
        "В Hazy IPA чувствуется манго, но в составе нет фруктов. Какое объяснение подходит?",
        ("Хмельная ароматика", "Молочная кислотность", "Солодовая карамель"),
        0,
        "Хмели могут создавать фруктовые ассоциации без добавления манго.",
    ),
    (
        "В одном меню есть Gose и Gueuze. Как правильно их различить?",
        ("Разные традиции", "Одинаковые названия", "Случайные опечатки"),
        0,
        "Gose связан с немецким пшеничным пивом, солью и кориандром; Gueuze — с купажом бельгийских ламбиков.",
    ),
    (
        "На этикетке написано DDH. О какой стороне пива прежде всего идёт речь?",
        ("Плотность пива", "Охмеление пива", "Крепость пива"),
        1,
        "DDH раскрывается как Double Dry Hopped и относится к холодному охмелению.",
    ),
    (
        "На столе тёмный Irish Stout и золотистый Tripel. Чем надёжнее проверить, какой крепче?",
        ("Оттенком пива", "Плотностью пены", "Значением ABV"),
        2,
        "Цвет не даёт надёжной оценки крепости. У классического Tripel она часто выше, чем у Irish Stout.",
    ),
)


def escape(value):
    return str(value).translate(ESCAPES)


def table(head, rows):
    headers = "".join(f'<th scope="col">{escape(cell)}</th>' for cell in head)
    cells = ("".join(f"<td>{escape(cell)}</td>" for cell in row) for row in rows)
    body = "".join(f"<tr>{row}</tr>" for row in cells)
    return (
        f'<div class="table-wrap"><table><thead><tr>{headers}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def source_control(source, markup, label=None):
    aria = f' aria-label="{escape(label)}"' if label else ""
    return (
        f'<a class="source-fallback" href="{escape(source["url"])}"{aria}>{markup}</a>'
        f'<button type="button" class="source-trigger" popovertarget="source-popover:{source["id"]}" '
        f'aria-haspopup="dialog"{aria}>{markup}</button>'
    )


def source_popover(source):
    source_id = source["id"]
    popover_id = f"source-popover:{source_id}"
    title_id = f"source-popover-title:{source_id}"
    return f"""<dialog id="{popover_id}" class="source-popover" popover="auto" aria-labelledby="{title_id}">
  <small>Источник {source["n"]:02}</small>
  <button type="button" popovertarget="{popover_id}" popovertargetaction="hide" aria-label="Закрыть карточку источника" autofocus>×</button>
  <h2 id="{title_id}">{escape(source["title"])}</h2>
  <p>{escape(source["note"])}</p>
  <a href="{escape(source["url"])}" target="_blank" rel="noopener">Открыть в новой вкладке ↗</a>
  <a class="source-popover__jump" href="#source-{source_id}" target="_blank" rel="noopener" aria-describedby="{NEW_TAB_DESCRIPTION}">К записи в атласе</a>
</dialog>"""


def glass_path(color, haze):
    haze_path = (
        '<path d="M5 48H70M7 61H68M9 75H66" stroke="#faebc4" stroke-opacity=".3" stroke-width="5"/>'
        if haze
        else ""
    )
    return (
        '<g transform="translate(0 0)">'
        f'<path d="M0 0H74L65 146Q37 156 9 146Z" fill="{color}"/>'
        '<path d="M8 17L15 137" fill="none" stroke="#fffdf7" stroke-opacity=".36" stroke-width="4"/>'
        '<path d="M0 0Q8 -16 18 -6Q26 -20 37 -7Q49 -21 58 -6Q69 -17 74 0V13H0Z" fill="#f5edda"/>'
        f'{haze_path}<path d="M0 0L9 146Q37 156 65 146L74 0" fill="none" '
        'stroke="#fffdf7" stroke-width="2" stroke-opacity=".6"/></g>'
    )


def cover(atlas):
    glasses = (
        ("Солод", "lagers", "к лагерам", "#d69a2c", False),
        ("Хмель", "hops", "к IPA и APA", "#ddac54", True),
        ("Кислота", "sour", "к кислым стилям", "#a6516e", False),
        ("Обжарка", "dark", "к портерам и стаутам", "#30251c", False),
    )
    drawings = "".join(
        f"""<a class="cover-glass-link" href="#{section}" aria-label="{name}. Перейти {destination}">
  <figure class="cover-glass">
    <svg class="cover-glass-drawing" viewBox="-2 -22 78 178" width="78" height="178" aria-hidden="true" focusable="false">{glass_path(color, haze)}</svg>
    <figcaption>{name}</figcaption>
  </figure>
  <span class="cover-glass-arrow" aria-hidden="true">↘</span>
</a>"""
        for name, section, destination, color, haze in glasses
    )
    return (
        '<section id="start" class="sheet cover">'
        '<div class="eyebrow">ВИЗУАЛЬНЫЙ АТЛАС ПИВА</div>'
        '<div class="cover-grid"><div><h1>Погружение<br>в ПИВАС</h1>'
        f'<p class="lead">История, стили и вкус.<br>{escape(atlas["subtitle"])}</p></div>'
        '<div class="cover-art" role="group" '
        'aria-label="Четыре характера пива: солод, хмель, кислотность и обжарка">'
        f"{drawings}</div></div>"
        '<div class="cover-route">'
        "<div><b>История</b><span>От древних пайков до Hazy IPA</span></div>"
        f"<div><b>{len(atlas['styles'])} стиля и направления</b><span>От хеллеса до Hazy IPA</span></div>"
        "<div><b>Как выбрать</b><span>Сравнения, факты и немного практики</span></div></div>"
        '<div class="intro-links">'
        '<a href="#hops"><b>IPA / APA</b>Хмельный характер</a>'
        '<a href="#sour"><b>Gose / Sour</b>Варианты кислотности</a>'
        '<a href="#school-central"><b>Пивные школы</b>Страны и их истории</a>'
        '<a href="#label"><b>Этикетки</b>Перевод сокращений</a>'
        '<a href="#quick"><b>Шпаргалка</b>Ориентиры для меню</a></div></section>'
    )


def quiz_html():
    blocks = []
    for index, (question, choices, answer, explanation) in enumerate(QUIZ, 1):
        buttons = "".join(
            f'<button type="button" data-choice="{choice_id}">{escape(choice)}</button>'
            for choice_id, choice in enumerate(choices)
        )
        blocks.append(
            f'<div class="quiz" data-quiz data-answer="{answer}" data-explain="{escape(explanation)}">'
            f'<h3>{index}. {escape(question)}</h3><div class="quiz-options">{buttons}</div>'
            '<p class="quiz-feedback" aria-live="polite"></p></div>'
        )
    return "".join(blocks)


class AtlasPage:
    def __init__(self, atlas, chapters, sources):
        self.atlas = atlas
        self.sources = sources
        self.styles = {style["id"]: style for style in atlas["styles"]}
        self.source_by_id = {source["id"]: source for source in sources}
        self.chapters = [dict(chapter, number=f"{i:02}") for i, chapter in enumerate(chapters, 1)]
        self.sections = {
            section["id"]: dict(
                section,
                group=chapter["group"],
                number=chapter["number"] + (f".{i}" if len(chapter["sections"]) > 1 else ""),
            )
            for chapter in self.chapters
            for i, section in enumerate(chapter["sections"], 1)
        }
        if list(self.sections) != [*(page["id"] for page in atlas["pages"]), "practice", "sources"]:
            raise ValueError(
                "Chapter outline must contain every section exactly once and in reading order"
            )

    def refs(self, ids):
        if not ids:
            return ""
        controls = []
        for source_id in ids:
            source = self.source_by_id.get(source_id)
            if source is None:
                raise ValueError(f"Unknown source ID: {source_id}")
            number = f"[{source['n']:02}]"
            controls.append(
                source_control(
                    source, number, f"{number} — Источник {source['n']}: {source['title']}"
                )
            )
        return '<div class="refs">Источники: ' + "".join(controls) + "</div>"

    def style_card(self, style):
        return (
            f'<article id="style-{style["id"]}" class="style-card" data-family="{escape(style["family"])}">'
            f'<h3>{escape(style["name"])}</h3><div class="style-sub">{escape(style["sub"])}</div>'
            f'<div class="style-stats"><span><b>ABV</b> {escape(style["abv"])}</span>'
            f"<span><b>IBU</b> {escape(style['ibu'])}</span></div>"
            f"<p><b>Вкус</b>{escape(style['taste'])}</p><p><b>История</b>{escape(style['origin'])}</p>"
            f"<p><b>Отличие</b>{escape(style['difference'])}</p>{self.refs(style.get('refs'))}</article>"
        )

    def story(self, item):
        paragraphs = "".join(f"<p>{escape(text)}</p>" for text in item["paragraphs"])
        palate = (
            f'<p class="story-palate">{escape(item["palate"])}</p>' if item.get("palate") else ""
        )
        return (
            f'<article class="history-story" id="{escape(item["id"])}">'
            f'<div class="story-kicker">{escape(item["kicker"])}</div><h3>{escape(item["title"])}</h3>'
            f"{paragraphs}{palate}{self.refs(item.get('refs'))}</article>"
        )

    def block(self, block):
        kind = block["type"]
        items = block.get("items", ())
        references = self.refs(block.get("refs"))
        match kind:
            case "stories":
                html = '<div class="history-stories">' + "".join(map(self.story, items)) + "</div>"
            case "layers":
                rows = (
                    f'<div class="layer"><span>{escape(a)}</span><b>{escape(b)}</b><p>{escape(c)}</p></div>'
                    for a, b, c in items
                )
                html = '<div class="layers">' + "".join(rows) + "</div>"
            case "cards" | "myths":
                card_class = "card" if kind == "cards" else "myth"
                rows = (
                    f'<article class="{card_class}"><h3>{escape(item["title"])}</h3>'
                    f"<p>{escape(item['text'])}</p>{self.refs(item.get('refs'))}</article>"
                    for item in items
                )
                html = f'<div class="{kind}">' + "".join(rows) + "</div>"
            case "axes" | "ingredients":
                unit = "axis" if kind == "axes" else "ingredient"
                rows = (
                    f'<div class="{unit}"><b>{escape(a)}</b><span>{escape(b)}</span></div>'
                    for a, b in items
                )
                html = f'<div class="{kind}">' + "".join(rows) + "</div>"
            case "callout":
                return (
                    f'<aside class="callout"><div class="label">{escape(block["label"])}</div>'
                    f"<p>{escape(block['text'])}</p>{references}</aside>"
                )
            case "timeline":
                rows = (
                    f'<li class="timeline__event"><div class="timeline__date">{escape(item["date"])}</div>'
                    f'<div><h3 class="timeline__title">{escape(item["title"])}</h3>'
                    f'<p class="timeline__text">{escape(item["text"])}</p>{self.refs(item.get("refs"))}</div></li>'
                    for item in items
                )
                html = '<ol class="timeline">' + "".join(rows) + "</ol>"
            case "styles":
                variant = "three" if len(block["ids"]) == 3 else ""
                rows = (self.style_card(self.styles[style_id]) for style_id in block["ids"])
                html = f'<div class="style-grid {variant}">' + "".join(rows) + "</div>"
            case "table":
                html = table(block["head"], block["rows"])
            case "process":
                rows = (
                    f'<div class="step"><b>{escape(a)}</b><p>{escape(b)}</p></div>'
                    for a, b in items
                )
                html = '<div class="process">' + "".join(rows) + "</div>"
            case "labels":
                rows = (
                    '<article class="label-example"><div class="example-tag">Пример этикетки · вымышленное пиво</div>'
                    f'<h3>{escape(item["name"])}</h3><p class="stats">{escape(item["stats"])}</p>'
                    f'<p class="notes">{escape(item["notes"])}</p><p class="explain">{escape(item["explain"])}</p></article>'
                    for item in items
                )
                html = '<div class="labels">' + "".join(rows) + "</div>"
            case "quicktable":
                styles = (self.styles[style_id] for style_id in QUICK_STYLES)
                rows = ((style["name"], style["taste"], style["abv"]) for style in styles)
                html = table(("Стиль / направление", "Характер", "ABV: ориентир"), rows)
            case "recall":
                rows = (
                    f"<details><summary>{escape(a)}</summary><p>{escape(b)}</p></details>"
                    for a, b in items
                )
                html = (
                    '<div class="recall"><h3>Три вопроса для самопроверки</h3>'
                    + "".join(rows)
                    + "</div>"
                )
            case _:
                raise ValueError(f"Unknown block {kind}")
        return html + references

    def heading(self, section_id, title):
        title = re.sub(r"^\d+(?:\.\d+)*\s*/\s*", "", title)
        return f'<div class="eyebrow">{self.sections[section_id]["number"]} / {escape(title)}</div>'

    def footer(self, section_id):
        number = self.sections[section_id]["number"]
        return f'<footer class="chapter-footer"><span>ПОГРУЖЕНИЕ В ПИВАС</span><span>РАЗДЕЛ {number}</span></footer>'

    def compare_data(self):
        fields = ("name", "abv", "ibu", "taste", "difference")
        return {
            style_id: {field: self.styles[style_id][field] for field in fields}
            for style_id in COMPARE_STYLES
        }

    def page(self, page, compare):
        section_id = page["id"]
        note = compare_box = ""
        if section_id == "hops":
            note = (
                '<p class="reading-note">Значения ABV и IBU ниже — ориентиры BJCP 2021 для указанных профилей. '
                "Конкретное пиво может выходить за эти диапазоны, а сами диапазоны могут пересекаться.</p>"
            )
            buttons = "".join(
                f'<button type="button" data-style="{style_id}" aria-pressed="false">{escape(style["name"])}</button>'
                for style_id, style in compare.items()
            )
            compare_box = (
                '<div id="style-compare" class="compare-block no-print"><h3>Сравнение хмелевых профилей</h3>'
                "<p>Для сравнения выберите до двух стилей. При выборе третьего заменяется первый.</p>"
                f'<div class="compare-picker">{buttons}</div>'
                '<div class="table-wrap" data-compare-output aria-live="polite"></div></div>'
            )
        blocks = "".join(map(self.block, page["blocks"]))
        return (
            f'<section id="{section_id}" class="sheet">{self.heading(section_id, page["eyebrow"])}'
            f'<h2>{escape(page["title"])}</h2><p class="lead">{escape(page["lead"])}</p>'
            f"{note}{blocks}{compare_box}{self.footer(section_id)}</section>"
        )

    def practice(self):
        return (
            '<section id="practice" class="sheet">'
            f"{self.heading('practice', 'САМОПРОВЕРКА · 3 МИНУТЫ')}<h2>Четыре вопроса о пиве</h2>"
            '<p class="lead">Чем отличаются похожие названия и что скрывается за сокращениями? '
            "После выбора ответа появится короткое объяснение.</p>"
            f'{quiz_html()}<p class="reading-note">Основные различия собраны в '
            '<a href="#quick">шпаргалке для меню</a>, а подробности о сокращениях — в разделе '
            f'<a href="#label">об этикетках</a>.</p>{self.footer("practice")}</section>'
        )

    def bibliography(self):
        entries = []
        for source in self.sources:
            title = f'<span class="source-entry__number">{source["n"]:02}</span> {escape(source["title"])}'
            entries.append(
                f'<article class="source-entry" id="source-{source["id"]}">{source_control(source, title)}'
                f"<p>{escape(source['note'])}</p><small>{escape(urlsplit(source['url']).hostname)}</small></article>"
            )
        return (
            f'<section id="sources" class="sheet">{self.heading("sources", "ДЛЯ ДАЛЬНЕЙШЕГО ЧТЕНИЯ")}'
            '<h2>Источники и пояснения</h2><p class="lead">Основа описаний — BJCP Beer Style Guidelines 2021. '
            "Для современных направлений дополнительно использованы Brewers Association 2026 и объяснения пивоварен.</p>"
            '<p class="reading-note">Справочники описывают типичный профиль; названия в меню не всегда совпадают '
            "с конкурсными категориями. Легенды и исторические реконструкции отмечены отдельно. "
            "Вкусовые сравнения помогают представить пиво и не заменяют перечень ингредиентов.</p>"
            f'<div class="source-grid">{"".join(entries)}</div>{self.footer("sources")}</section>'
        )

    def body(self, compare):
        links = "".join(
            f'<a href="#{escape(chapter["sections"][0]["id"])}" data-section-link="{escape(chapter["group"])}">'
            f"<span>{chapter['number']}</span>{escape(chapter['title'])}</a>"
            for chapter in self.chapters
        )
        nav = (
            '<nav class="topnav" aria-label="Навигация по атласу"><div class="nav-main">'
            '<a class="brand" href="#start" data-section-link="start">ПОГРУЖЕНИЕ В ПИВАС</a>'
            '<details class="header-index"><summary>Содержание</summary>'
            f'<nav aria-label="Быстрый переход по атласу">{links}</nav></details></div>'
            '<div class="reading-location"><span class="reading-location-label">Сейчас читаете</span>'
            '<span class="reading-title" data-current-section-title role="status" aria-live="polite" '
            'aria-atomic="true">Начало</span></div>'
            '<div class="reading-progress" aria-hidden="true"><span></span></div></nav>'
        )
        sidebar = (
            '<aside class="atlas-sidebar" aria-label="Оглавление атласа">'
            '<p class="index-label">Путеводитель по атласу</p>'
            f'<nav aria-label="Главы атласа">{links}</nav></aside>'
        )
        mobile_index = (
            '<details class="atlas-mobile-index"><summary>Содержание атласа</summary>'
            f'<nav aria-label="Содержание на небольшом экране">{links}</nav></details>'
        )
        pages = "".join(self.page(page, compare) for page in self.atlas["pages"])
        popovers = "\n".join(map(source_popover, self.sources))
        body = (
            f'{nav}<main id="atlas-content">{cover(self.atlas)}<div class="atlas-layout">{sidebar}'
            f'<div class="atlas-content">{mobile_index}{pages}{self.practice()}{self.bibliography()}</div></div></main>'
            f'<span id="{NEW_TAB_DESCRIPTION}" hidden>Откроется в новой вкладке</span>\n{popovers}'
        )
        return re.sub(r'<section id="([^"]+)" class="sheet([^"]*)">', self.annotate_section, body)

    def annotate_section(self, match):
        section_id, classes = match.groups()
        section = (
            {"group": "start", "readingTitle": "Начало"}
            if section_id == "start"
            else self.sections[section_id]
        )
        return (
            f'<section id="{escape(section_id)}" class="sheet{classes}" data-nav-group="{escape(section["group"])}" '
            f'data-reading-title="{escape(section["readingTitle"])}" tabindex="-1">'
        )


def page_metadata(title, site):
    title = escape(title)
    description = escape(site["description"])
    url = escape(site["url"])
    image_url = escape(urljoin(site["url"], "assets/social-cover.jpg"))
    image = {key: escape(value) for key, value in site["image"].items()}
    return f"""<title>{title}</title>
<meta name="description" content="{description}">
<meta name="keywords" content="{escape(", ".join(site["keywords"]))}">
<meta name="robots" content="max-image-preview:large">
<meta name="theme-color" content="{THEME_COLOR}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="{title}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image_url}">
<meta property="og:image:type" content="{image["type"]}">
<meta property="og:image:width" content="{image["width"]}">
<meta property="og:image:height" content="{image["height"]}">
<meta property="og:image:alt" content="{image["alt"]}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image_url}">
<meta name="twitter:image:alt" content="{image["alt"]}">"""


def build(root=ROOT):
    assets = root / "assets"
    atlas = read_json(assets / "beer-data.json")
    chapters = read_json(assets / "atlas-chapters.json")
    site = read_json(assets / "site-metadata.json")
    sources = read_sources(assets / "beer-sources.md")
    page = AtlasPage(atlas, chapters, sources)
    compare = page.compare_data()
    compare_json = json.dumps(compare, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    styles = "\n".join(
        (assets / name).read_bytes().decode() for name in ("beer.css", "atlas-layout.css")
    )
    # Inline browser modules also work when the page is opened from disk.
    script = "\n".join(
        (assets / name).read_bytes().decode()
        for name in ("learning.js", "navigation.js", "source-popovers.js")
    )
    document = f"""<!doctype html>
<html lang="ru" prefix="og: https://ogp.me/ns#"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{page_metadata(atlas["title"], site)}
<link rel="icon" href="favicon.ico" sizes="32x32">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png" sizes="180x180">
<link rel="manifest" href="manifest.webmanifest">
<style>
{styles}
</style></head><body class="atlas-page"><a class="skip-link" href="#map">Перейти к содержанию</a>{page.body(compare)}<script type="application/json" id="compare-data">{compare_json}</script>
<script type="module">{script}</script>
</body></html>"""
    manifest = {
        "id": urlsplit(site["url"]).path,
        "name": atlas["title"],
        "short_name": "ПИВАС",
        "lang": "ru",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "theme_color": THEME_COLOR,
        "background_color": "#faf6ed",
        "icons": [
            {"src": "icon-192.png", "type": "image/png", "sizes": "192x192"},
            {
                "src": "icon-mask.png",
                "type": "image/png",
                "sizes": "512x512",
                "purpose": "maskable",
            },
            {"src": "icon-512.png", "type": "image/png", "sizes": "512x512"},
        ],
    }
    index = root / "index.html"
    index.write_bytes(document.encode())
    (root / MANIFEST).write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    )
    (root / ".nojekyll").write_bytes(b"")
    return {"index": str(index), "styles": len(atlas["styles"]), "sources": len(sources)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate the HTML and web manifest.")
    parser.parse_args(argv)
    try:
        print(json.dumps(build()))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()

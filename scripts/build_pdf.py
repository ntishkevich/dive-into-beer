import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepInFrame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from read_sources import read_sources

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "output" / "beer-atlas.pdf"
DEFAULT_FONT_DIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
QA_PATH = ROOT / "tmp" / "pdf-check.json"
SOURCES_PER_PAGE = 17

PAPER = colors.HexColor("#faf6ed")
INK = colors.HexColor("#183b34")
MUTED = colors.HexColor("#59665d")
LINE = colors.HexColor("#d9d7c8")
AMBER = colors.HexColor("#b35b16")
HOP = colors.HexColor("#527142")
SOFT = colors.HexColor("#eee8d9")
PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN = 37
PRINT_WIDTH = PAGE_WIDTH - PAGE_MARGIN * 2
PARAGRAPH_STYLES = {
    "body": ParagraphStyle(
        "body", fontName="Text", fontSize=9.05, leading=12.2, textColor=INK, spaceAfter=5
    ),
    "lead": ParagraphStyle(
        "lead", fontName="Text", fontSize=10.2, leading=14, textColor=MUTED, spaceAfter=13
    ),
    "title": ParagraphStyle(
        "title", fontName="Display", fontSize=27, leading=30, textColor=INK, spaceAfter=11
    ),
    "eyebrow": ParagraphStyle(
        "eyebrow", fontName="Text-Bold", fontSize=7.3, leading=10.5, textColor=AMBER, spaceAfter=12
    ),
    "h3": ParagraphStyle(
        "h3", fontName="Display", fontSize=16, leading=18, textColor=INK, spaceAfter=8
    ),
    "h4": ParagraphStyle(
        "h4", fontName="Display", fontSize=13.6, leading=16, textColor=INK, spaceAfter=7
    ),
    "sub": ParagraphStyle(
        "sub", fontName="Text", fontSize=7.6, leading=10, textColor=MUTED, spaceAfter=8
    ),
    "stats": ParagraphStyle(
        "stats", fontName="Text-Bold", fontSize=8, leading=11, textColor=AMBER, spaceAfter=8
    ),
    "ref": ParagraphStyle(
        "ref", fontName="Text", fontSize=6.7, leading=9, textColor=MUTED, spaceAfter=6
    ),
    "table": ParagraphStyle("table", fontName="Text", fontSize=8.2, leading=11, textColor=INK),
    "th": ParagraphStyle("th", fontName="Text-Bold", fontSize=7.2, leading=9.5, textColor=INK),
    "small": ParagraphStyle(
        "small", fontName="Text", fontSize=8.1, leading=10.8, textColor=MUTED, spaceAfter=7
    ),
    "date": ParagraphStyle(
        "date", fontName="Display", fontSize=13.6, leading=16, textColor=AMBER, spaceAfter=5
    ),
    "answer": ParagraphStyle(
        "answer", fontName="Text", fontSize=8.2, leading=11, textColor=MUTED, spaceAfter=8
    ),
    "story": ParagraphStyle(
        "story", fontName="Text", fontSize=9.6, leading=13.6, textColor=INK, spaceAfter=8
    ),
    "palate": ParagraphStyle(
        "palate", fontName="Text-Italic", fontSize=8.7, leading=12, textColor=HOP, spaceAfter=6
    ),
}


def escape_text(s):
    return (
        html.escape(str(s))
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("\u2011", "-")
    )


def paragraph(s, style="body", raw=False):
    return Paragraph(s if raw else escape_text(s), PARAGRAPH_STYLES[style])


def styled_table(rows, widths, header=False, soft=False):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        commands += [
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
        ]
    if soft:
        commands += [("BACKGROUND", (0, 0), (-1, -1), SOFT)]
    t.setStyle(TableStyle(commands))
    return t


def pairs(cells, soft=False, lines=False):
    result = []
    for i in range(0, len(cells), 2):
        group = cells[i : i + 2]
        widths = (
            [(PRINT_WIDTH - 14) / 2, 14, (PRINT_WIDTH - 14) / 2]
            if len(group) == 2
            else [PRINT_WIDTH]
        )
        row = [group[0], [], group[1]] if len(group) == 2 else [group[0]]
        t = styled_table([row], widths)
        commands = []
        if soft:
            commands += [("BACKGROUND", (0, 0), (0, 0), SOFT)]
            if len(group) == 2:
                commands += [("BACKGROUND", (2, 0), (2, 0), SOFT)]
        if lines:
            commands += [("LINEABOVE", (0, 0), (0, 0), 1.7, HOP)]
            if len(group) == 2:
                commands += [("LINEABOVE", (2, 0), (2, 0), 1.7, HOP)]
        t.setStyle(TableStyle(commands))
        result.extend([t, Spacer(1, 7)])
    return result


class Cover(Flowable):
    def __init__(self, style_count):
        super().__init__()
        self.style_count = style_count
        self.width = PRINT_WIDTH
        self.height = PAGE_HEIGHT - PAGE_MARGIN * 2 - 4

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#e6b970"))
        c.setFont("Text-Bold", 9)
        c.drawString(2, 731, "ВИЗУАЛЬНЫЙ АТЛАС ПИВА")
        c.setFillColor(PAPER)
        c.setFont("Display", 53)
        c.drawString(0, 654, "Погружение")
        c.setFont("Display", 59)
        c.drawString(0, 585, "в ПИВАС")
        c.setFont("Text", 15)
        c.drawString(2, 541, "История, стили и вкус.")
        c.setFont("Text", 11)
        c.setFillColor(colors.HexColor("#d2dace"))
        c.drawString(2, 518, "Как появились пивные стили, чем они отличаются")
        c.drawString(2, 500, "и откуда берутся знакомые вкусы.")
        labels = ["СОЛОД", "ХМЕЛЬ", "КИСЛОТА", "ОБЖАРКА"]
        fills = ["#d69a2c", "#ddac54", "#a6516e", "#30251c"]
        for i in range(4):
            x = 22 + i * 130
            y = 281
            c.setFillColor(colors.HexColor(fills[i]))
            q = c.beginPath()
            q.moveTo(x, y + 144)
            q.lineTo(x + 79, y + 144)
            q.lineTo(x + 68, y + 1)
            q.curveTo(x + 49, y - 6, x + 30, y - 6, x + 11, y + 1)
            q.close()
            c.drawPath(q, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#f7edda"))
            c.setLineWidth(1)
            c.drawPath(q, fill=0, stroke=1)
            c.setFillColor(colors.HexColor("#f7edda"))
            c.roundRect(x, y + 132, 79, 21, 8, stroke=0, fill=1)
            c.setFillColor(colors.HexColor("#e6b970"))
            c.setFont("Text-Bold", 8)
            c.drawCentredString(x + 40, y - 27, labels[i])
        c.setStrokeColor(colors.HexColor("#6c8475"))
        c.setLineWidth(0.6)
        c.line(0, 213, PRINT_WIDTH, 213)
        for i, (title, detail) in enumerate(
            [
                ("История", "От древних пайков до IPA"),
                (str(self.style_count) + " стиля\nи направления", "От хеллеса до Hazy IPA"),
                ("Как выбрать", "Сравнения, факты и практика"),
            ]
        ):
            x = i * (PRINT_WIDTH / 3)
            c.setFillColor(colors.HexColor("#e6b970"))
            c.setFont("Display", 19)
            for line_index, line in enumerate(title.split("\n")):
                c.drawString(x, 171 - line_index * 22, line)
            c.setFillColor(colors.HexColor("#d2dace"))
            c.setFont("Text", 8)
            c.drawString(x, 129, detail)


def on_page(c, doc):
    c.saveState()
    if doc.page == 1:
        c.setFillColor(INK)
        c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    else:
        c.setFillColor(PAPER)
        c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.line(PAGE_MARGIN, 29, PAGE_WIDTH - PAGE_MARGIN, 29)
        c.setFont("Text", 7)
        c.setFillColor(MUTED)
        c.drawString(PAGE_MARGIN, 17, "ПОГРУЖЕНИЕ В ПИВАС  /  ВИЗУАЛЬНЫЙ АТЛАС")
        c.drawRightString(PAGE_WIDTH - PAGE_MARGIN, 17, str(doc.page).zfill(2))
    c.restoreState()


class AtlasLayout:
    def __init__(self, atlas, sources, chapters):
        self.atlas = atlas
        self.sources = sources
        self.sources_by_id = {source["id"]: source for source in sources}
        self.styles_by_id = {style["id"]: style for style in atlas["styles"]}
        self.section_numbers = {
            section["id"]: f"{chapter_number:02}"
            + (f".{section_number}" if len(chapter["sections"]) > 1 else "")
            for chapter_number, chapter in enumerate(chapters, 1)
            for section_number, section in enumerate(chapter["sections"], 1)
        }

    def _source_references(self, ids):
        if not ids:
            return []
        missing = set(ids) - self.sources_by_id.keys()
        if missing:
            raise ValueError(
                f"Source catalogue is missing IDs: {', '.join(sorted(missing))}. "
                "Export it again with python scripts/atlas.py sources --output <file>."
            )
        text = "Источники: " + " ".join(
            '<a href="'
            + escape_text(self.sources_by_id[source_id]["url"])
            + '" color="#59665d">['
            + str(self.sources_by_id[source_id]["n"]).zfill(2)
            + "]</a>"
            for source_id in ids
        )
        return [paragraph(text, "ref", True)]

    def _style_cell(self, style):
        flowables = [
            paragraph(style["name"], "h3"),
            paragraph(style["sub"], "sub"),
            paragraph("ABV " + style["abv"] + "   |   IBU " + style["ibu"], "stats"),
        ]
        for key, label in [("taste", "Вкус"), ("origin", "История"), ("difference", "Отличие")]:
            flowables.append(
                paragraph("<b>" + label + ".</b> " + escape_text(style[key]), raw=True)
            )
        return flowables + self._source_references(style["refs"])

    def _text_card(self, card):
        return [paragraph(card["title"], "h4"), paragraph(card["text"])] + self._source_references(
            card.get("refs")
        )

    def _render_block(self, block):
        flowables = []
        block_type = block["type"]
        if block_type == "stories":
            for x in block["items"]:
                flowables.extend(
                    [
                        HRFlowable(width="100%", thickness=0.5, color=LINE),
                        Spacer(1, 11),
                        paragraph(x["kicker"], "eyebrow"),
                        paragraph(x["title"], "h3"),
                    ]
                )
                flowables.extend(paragraph(text, "story") for text in x["paragraphs"])
                if x.get("palate"):
                    flowables.append(paragraph(x["palate"], "palate"))
                flowables.extend(self._source_references(x["refs"]) + [Spacer(1, 12)])
        elif block_type == "layers":
            rows = [
                [paragraph(r[0], "small"), paragraph(r[1], "h4"), paragraph(r[2])]
                for r in block["items"]
            ]
            flowables = [styled_table(rows, [77, 155, PRINT_WIDTH - 232]), Spacer(1, 12)]
        elif block_type == "cards":
            flowables = pairs([self._text_card(x) for x in block["items"]], soft=True)
        elif block_type in ("axes", "ingredients"):
            cells = [[paragraph(r[0], "h4"), paragraph(r[1], "small")] for r in block["items"]]
            flowables = [
                styled_table([cells], [PRINT_WIDTH / len(cells)] * len(cells)),
                Spacer(1, 10),
            ]
        elif block_type == "callout":
            cell = [
                paragraph(block["label"].upper(), "eyebrow"),
                paragraph(block["text"]),
            ] + self._source_references(block.get("refs"))
            table = styled_table([[cell]], [PRINT_WIDTH], soft=True)
            table.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, 0), 2.6, HOP)]))
            return [Spacer(1, 8), table, Spacer(1, 8)]
        elif block_type == "timeline":
            rows = [
                [
                    paragraph(x["date"], "date"),
                    [paragraph(x["title"], "h4"), paragraph(x["text"])]
                    + self._source_references(x.get("refs")),
                ]
                for x in block["items"]
            ]
            table = styled_table(rows, [111, PRINT_WIDTH - 111])
            table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE)]))
            flowables = [table, Spacer(1, 10)]
        elif block_type == "styles":
            flowables = pairs(
                [self._style_cell(self.styles_by_id[x]) for x in block["ids"]], lines=True
            )
        elif block_type == "table":
            rows = [[paragraph(x, "th") for x in block["head"]]] + [
                [paragraph(x, "table") for x in row] for row in block["rows"]
            ]
            cols = len(block["head"])
            widths = (
                [PRINT_WIDTH * 0.22, PRINT_WIDTH * 0.78]
                if cols == 2
                else [PRINT_WIDTH * 0.22, PRINT_WIDTH * 0.39, PRINT_WIDTH * 0.39]
            )
            flowables = [styled_table(rows, widths, header=True), Spacer(1, 10)]
        elif block_type == "process":
            cells = [
                [paragraph(str(i + 1).zfill(2), "date"), paragraph(r[0], "h4"), paragraph(r[1])]
                for i, r in enumerate(block["items"])
            ]
            flowables = []
            for i in range(0, len(cells), 3):
                group = cells[i : i + 3]
                row = []
                widths = []
                for j, cell in enumerate(group):
                    if j:
                        row.append([])
                        widths.append(9)
                    row.append(cell)
                    widths.append((PRINT_WIDTH - 9 * (len(group) - 1)) / len(group))
                flowables.extend([styled_table([row], widths), Spacer(1, 6)])
        elif block_type == "labels":
            cells = []
            for x in block["items"]:
                cells.append(
                    [
                        paragraph("ПРИМЕР ЭТИКЕТКИ: ВЫМЫШЛЕННОЕ ПИВО", "sub"),
                        paragraph(x["name"], "h3"),
                        paragraph(x["stats"], "stats"),
                        paragraph(x["notes"], "small"),
                        paragraph(x["explain"]),
                    ]
                )
            flowables = pairs(cells, soft=True)
        elif block_type == "myths":
            flowables = pairs([self._text_card(x) for x in block["items"]])
        elif block_type == "quicktable":
            ids = [
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
            ]
            rows = [
                [paragraph(x, "th") for x in ["Стиль / направление", "Характер", "ABV: ориентир"]]
            ]
            rows += [
                [
                    paragraph(self.styles_by_id[x]["name"], "table"),
                    paragraph(self.styles_by_id[x]["taste"], "table"),
                    paragraph(self.styles_by_id[x]["abv"], "table"),
                ]
                for x in ids
            ]
            flowables = [
                styled_table(
                    rows, [PRINT_WIDTH * 0.23, PRINT_WIDTH * 0.55, PRINT_WIDTH * 0.22], header=True
                ),
                Spacer(1, 16),
            ]
        elif block_type == "recall":
            flowables = [paragraph("Три вопроса для самопроверки", "h3")]
            for r in block["items"]:
                flowables.extend(
                    [paragraph(r[0], "body"), paragraph("Подсказка: " + r[1], "answer")]
                )
        else:
            raise ValueError(block_type)
        return flowables + self._source_references(block.get("refs"))

    def build_story(self):
        story = [Cover(len(self.atlas["styles"])), PageBreak()]
        fit_groups = []
        for page in self.atlas["pages"]:
            eyebrow = re.sub(r"^\d+(?:\.\d+)*\s*/\s*", "", page["eyebrow"])
            group = [
                paragraph(f"{self.section_numbers[page['id']]} / {eyebrow}", "eyebrow"),
                paragraph(page["title"], "title"),
                paragraph(page["lead"], "lead"),
            ]
            if page["id"] == "hops":
                group.append(
                    paragraph(
                        "Числа ниже - диапазоны BJCP 2021 для указанных профилей, а не обязательные пределы коммерческих версий. Пересечение диапазонов нормально.",
                        "small",
                    )
                )
            for block in page["blocks"]:
                group.extend(self._render_block(block))
            fitted = KeepInFrame(
                PRINT_WIDTH,
                PAGE_HEIGHT - PAGE_MARGIN - 40,
                group,
                mode="shrink",
                hAlign="LEFT",
                vAlign="TOP",
            )
            fit_groups.append((page["id"], fitted))
            story.append(fitted)
            story.append(PageBreak())
        source_page_count = (len(self.sources) + SOURCES_PER_PAGE - 1) // SOURCES_PER_PAGE
        for idx in range(source_page_count):
            group = [
                paragraph(
                    f"{self.section_numbers['sources']} / ИСТОЧНИКИ · {idx + 1} ИЗ {source_page_count}",
                    "eyebrow",
                ),
                paragraph("Источники и пояснения", "title"),
            ]
            group.append(
                paragraph(
                    "BJCP 2021 задаёт ориентиры профилей; Brewers Association 2026 дополняет современную карту. Названия на рынке могут использоваться свободнее. Ссылки кликабельны.",
                    "lead",
                )
            )
            cells = []
            for s in self.sources[idx * SOURCES_PER_PAGE : (idx + 1) * SOURCES_PER_PAGE]:
                title = (
                    '<font color="#b35b16">'
                    + str(s["n"]).zfill(2)
                    + '</font>  <a href="'
                    + escape_text(s["url"])
                    + '"><b>'
                    + escape_text(s["title"])
                    + "</b></a>"
                )
                cells.append(
                    [
                        paragraph(title, "body", True),
                        paragraph(s["note"], "small"),
                        paragraph(urlparse(s["url"]).hostname, "ref"),
                    ]
                )
            group.extend(pairs(cells))
            fitted = KeepInFrame(
                PRINT_WIDTH,
                PAGE_HEIGHT - PAGE_MARGIN - 40,
                group,
                mode="shrink",
                hAlign="LEFT",
                vAlign="TOP",
            )
            fit_groups.append(("sources" + str(idx + 1), fitted))
            story.append(fitted)
            if idx < source_page_count - 1:
                story.append(PageBreak())
        return story, fit_groups


def register_fonts(directory):
    fonts = {
        "Text": "arial.ttf",
        "Text-Bold": "arialbd.ttf",
        "Text-Italic": "ariali.ttf",
        "Display": "georgia.ttf",
    }
    for name, filename in fonts.items():
        font_path = directory / filename
        if not font_path.is_file():
            raise FileNotFoundError(
                f"Font not found: {font_path}. Pass --font-dir with the required fonts."
            )
        pdfmetrics.registerFont(TTFont(name, str(font_path)))
    pdfmetrics.registerFontFamily(
        "Text", normal="Text", bold="Text-Bold", italic="Text-Italic", boldItalic="Text-Bold"
    )


def write_pdf_check(output, fit_groups):
    reader = PdfReader(output)
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pages.append({"page": number, "chars": len(text), "start": text[:95].replace("\n", " / ")})
    report = {
        "file": str(output),
        "pages": len(pages),
        "fit_scales": {key: round(getattr(item, "_scale", 1), 3) for key, item in fit_groups},
        "page_summary": pages,
    }
    QA_PATH.parent.mkdir(parents=True, exist_ok=True)
    QA_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "pages": report["pages"],
        "fit_scales": report["fit_scales"],
        "page_chars": [page["chars"] for page in pages],
    }


def build_pdf(output, font_dir, sources):
    if output.resolve() == QA_PATH.resolve() or (
        output.exists() and QA_PATH.exists() and output.samefile(QA_PATH)
    ):
        raise ValueError(f"PDF destination must differ from the QA report path: {QA_PATH}")
    atlas = json.loads((ROOT / "assets/beer-data.json").read_text(encoding="utf-8"))
    chapters = json.loads((ROOT / "assets/atlas-chapters.json").read_text(encoding="utf-8"))
    register_fonts(font_dir)
    story, fit_groups = AtlasLayout(atlas, sources, chapters).build_story()
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=PAGE_MARGIN,
        leftMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=40,
        title=atlas["title"] + " - визуальный атлас",
        author="Погружение в ПИВАС",
        subject="История пива, стили и чтение меню",
    )
    frame = Frame(
        PAGE_MARGIN,
        40,
        PRINT_WIDTH,
        PAGE_HEIGHT - PAGE_MARGIN - 40,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="normal",
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=on_page)])
    doc.build(story)
    return write_pdf_check(output, fit_groups)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate the print atlas.")
    parser.add_argument(
        "--sources",
        help="exported source catalogue as JSON, or - for standard input. Defaults to the Markdown catalogue.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_PDF, help="PDF destination")
    parser.add_argument(
        "--font-dir", type=Path, default=DEFAULT_FONT_DIR, help="Arial and Georgia TTF directory"
    )
    args = parser.parse_args(argv)
    try:
        if args.sources is None:
            sources = read_sources()
        else:
            payload = (
                sys.stdin.buffer.read() if args.sources == "-" else Path(args.sources).read_bytes()
            )
            sources = json.loads(payload)
        source_fields = {"id", "n", "title", "note", "url"}
        if (
            not isinstance(sources, list)
            or not sources
            or any(
                not isinstance(source, dict) or not source_fields <= source.keys()
                for source in sources
            )
        ):
            raise ValueError(
                "Expected a source catalogue exported by python scripts/atlas.py sources."
            )
        result = build_pdf(args.output.resolve(), args.font_dir, sources)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()

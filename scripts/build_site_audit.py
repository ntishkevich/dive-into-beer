"""Render a standalone summary from the two verified Lighthouse profiles."""

import argparse
import gzip
import json
from datetime import datetime, timedelta, timezone
from html import escape

from read_sources import read_sources
from site_files import CATEGORIES, ROOT, read_audited_site, read_json, site_file_hashes

MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def format_number(value):
    integer, fraction = f"{value:,.2f}".split(".")
    integer = integer.replace(",", "\u00a0")
    fraction = fraction.rstrip("0")
    return f"{integer},{fraction}" if fraction else integer


def build_report():
    snapshot, reports = read_audited_site()
    hashes = site_file_hashes(snapshot)
    digest = hashes["index.html"]
    body = snapshot["index.html"].body
    gzip_size = len(gzip.compress(body, compresslevel=6, mtime=0))
    atlas = read_json(ROOT / "assets/beer-data.json")
    source_count = len(read_sources())
    minimum = min(report["scores"][category] for report in reports for category in CATEGORIES)
    today = datetime.now(timezone(timedelta(hours=3)))
    date = f"{today.day} {MONTHS[today.month - 1]} {today.year} г."
    score_rows = []
    metric_rows = []
    for report in reports:
        label = "Mobile" if report["device"] == "mobile" else "Desktop"
        row = f'<tr><th scope="row">{label}</th>'
        score_cells = "".join(
            f'<td class="score">{report["scores"][category]}</td>' for category in CATEGORIES
        )
        score_rows.append(f"{row}{score_cells}</tr>")
        metrics = report["metrics"]
        fcp = format_number(metrics["first-contentful-paint"]["value"] / 1000)
        lcp = format_number(metrics["largest-contentful-paint"]["value"] / 1000)
        tbt = int(metrics["total-blocking-time"]["value"] + 0.5)
        cls = format_number(metrics["cumulative-layout-shift"]["value"])
        metric_rows.append(
            f"{row}<td>{fcp} с</td><td>{lcp} с</td><td>{tbt} мс</td><td>{cls}</td></tr>"
        )
    report_styles = (ROOT / "assets/site-audit.css").read_text(encoding="utf-8")
    html = f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Погружение в ПИВАС — проверка готового сайта</title>
    <meta
      name="description"
      content="Результаты Lighthouse для готовой страницы с выбранным оформлением B"
    />
    <style>
      {report_styles}
    </style>
  </head>
  <body>
    <main>
      <p class="eyebrow">ПРОВЕРКА ГОТОВОЙ СТРАНИЦЫ · {date}</p>
      <h1>Погружение в ПИВАС:<br />выбран вариант B</h1>
      <p>
        Основная страница использует компоновку «Атлас»: боковое оглавление на компьютере и меню
        «Содержание» на телефоне. Панель выбора вариантов и переключение раскладок в готовый сайт не
        входят.
      </p>
      <div class="hero">
        <strong>{minimum} / 100</strong>Минимальная оценка среди четырёх категорий в двух проверках
        готовой страницы.
      </div>
      <h2>Lighthouse готовой версии</h2>
      <p>
        Проверен именно <code>index.html</code> после внедрения выбранного оформления. Lighthouse
        {escape(reports[0]["lighthouse"])}, штатные профили Mobile и Desktop.
      </p>
      <div class="wrap">
        <table>
          <thead>
            <tr>
              <th>Профиль</th>
              <th>Performance</th>
              <th>Accessibility</th>
              <th>Best Practices</th>
              <th>SEO</th>
            </tr>
          </thead>
          <tbody>
            {"".join(score_rows)}
          </tbody>
        </table>
      </div>
      <h2>Измеренные показатели</h2>
      <div class="wrap">
        <table>
          <thead>
            <tr>
              <th>Профиль</th>
              <th>FCP</th>
              <th>LCP</th>
              <th>TBT</th>
              <th>CLS</th>
            </tr>
          </thead>
          <tbody>
            {"".join(metric_rows)}
          </tbody>
        </table>
      </div>
      <p class="note">
        Это лабораторные замеры локального статического сайта с gzip. Mobile — эмуляция телефона с
        ограничениями сети и CPU. После публикации на GitHub Pages результат может отличаться из-за
        сети, сервера, нагрузки и версии браузера. INP в этих навигационных аудитах не измерялся.
      </p>
      <h2>Что сохранено и проверено</h2>
      <ul>
        <li>
          Название «Погружение в ПИВАС», рисунок с бокалами, исходная палитра и семейства шрифтов.
        </li>
        <li>
          Разделы — {len(atlas["pages"]) + 3}, профили пива — {len(atlas["styles"])}, источники —
          {source_count}. Есть сравнение хмелевых стилей и самопроверка.
        </li>
        <li>
          Боковое оглавление, мобильное меню, прямые ссылки на главы и обычная история переходов
          браузера.
        </li>
        <li>Подсветка текущей главы, её название и индикатор чтения в шапке.</li>
        <li>Короткие однократные анимации, которые отключаются при prefers-reduced-motion.</li>
        <li>
          Проверены ширины 320, 360, 768 и 1200 пикселей. Текст и оглавление доступны без
          JavaScript.
        </li>
        <li>
          Готовый HTML не требует сборки, внешних шрифтов и дополнительных библиотек. Размер:
          {format_number(len(body) / 1024)} КиБ; с gzip: {format_number(gzip_size)} КиБ.
        </li>
      </ul>
      <p>
        Полные отчёты Lighthouse в HTML и JSON находятся в <code>output/site-audits</code>. Архив
        <code>beer-site.zip</code> содержит сайт и инструкцию для размещения.
      </p>
      <p>
        <small>SHA-256 проверенного HTML: {digest}<br />Браузер: {escape(reports[0]["chrome"])}</small>
      </p>
    </main>
  </body>
</html>"""

    output = ROOT / "output"
    (output / "beer-design-audit.html").write_text(html, encoding="utf-8", newline="\n")
    summary = {
        "date": date,
        "layout": "B",
        "artifactSha256": digest,
        "siteFileHashes": hashes,
        "bytes": len(body),
        "gzipBytes": gzip_size,
        "minimumScore": minimum,
        "reports": reports,
    }
    (output / "beer-design-audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    return dict(layout="B", reports=len(reports), minimumScore=minimum, sha=digest)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize the Lighthouse results.")
    parser.parse_args(argv)
    try:
        print(json.dumps(build_report()))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
